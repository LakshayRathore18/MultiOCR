"""
Character Visualization Module for Sanskrit OCR
This module provides visualization capabilities including:
1. Character-level heatmaps using CRAFT model
2. Bounding boxes around each character
3. Line segmentation visualization
"""

import os
import numpy as np
import cv2
import torch
import torch.nn.functional as F
from skimage import io
import torch.nn as nn
import torch.nn.init as init
import torchvision
from torchvision import models
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for server environments
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from collections import namedtuple
from packaging import version
from collections import OrderedDict
from scipy.signal import find_peaks

# ============================================================================
# CRAFT MODEL DEFINITION
# ============================================================================

def init_weights(modules):
    for m in modules:
        if isinstance(m, nn.Conv2d):
            init.xavier_uniform_(m.weight.data)
            if m.bias is not None:
                m.bias.data.zero_()
        elif isinstance(m, nn.BatchNorm2d):
            m.weight.data.fill_(1)
            m.bias.data.zero_()
        elif isinstance(m, nn.Linear):
            m.weight.data.normal_(0, 0.01)
            m.bias.data.zero_()

class vgg16_bn(torch.nn.Module):
    def __init__(self, pretrained=True, freeze=True):
        super(vgg16_bn, self).__init__()
        if version.parse(torchvision.__version__) >= version.parse('0.13'):
            vgg_pretrained_features = models.vgg16_bn(
                weights=models.VGG16_BN_Weights.DEFAULT if pretrained else None
            ).features
        else:
            models.vgg.model_urls['vgg16_bn'] = models.vgg.model_urls['vgg16_bn'].replace('https://', 'http://')
            vgg_pretrained_features = models.vgg16_bn(pretrained=pretrained).features

        self.slice1 = torch.nn.Sequential()
        self.slice2 = torch.nn.Sequential()
        self.slice3 = torch.nn.Sequential()
        self.slice4 = torch.nn.Sequential()
        self.slice5 = torch.nn.Sequential()
        for x in range(12):
            self.slice1.add_module(str(x), vgg_pretrained_features[x])
        for x in range(12, 19):
            self.slice2.add_module(str(x), vgg_pretrained_features[x])
        for x in range(19, 29):
            self.slice3.add_module(str(x), vgg_pretrained_features[x])
        for x in range(29, 39):
            self.slice4.add_module(str(x), vgg_pretrained_features[x])
            
        self.slice5 = torch.nn.Sequential(
                nn.MaxPool2d(kernel_size=3, stride=1, padding=1),
                nn.Conv2d(512, 1024, kernel_size=3, padding=6, dilation=6),
                nn.Conv2d(1024, 1024, kernel_size=1)
        )

        if not pretrained:
            init_weights(self.slice1.modules())
            init_weights(self.slice2.modules())
            init_weights(self.slice3.modules())
            init_weights(self.slice4.modules())

        init_weights(self.slice5.modules())

        if freeze:
            for param in self.slice1.parameters():
                param.requires_grad= False

    def forward(self, X):
        h = self.slice1(X)
        h_relu2_2 = h
        h = self.slice2(h)
        h_relu3_2 = h
        h = self.slice3(h)
        h_relu4_3 = h
        h = self.slice4(h)
        h_relu5_3 = h
        h = self.slice5(h)
        h_fc7 = h
        vgg_outputs = namedtuple("VggOutputs", ['fc7', 'relu5_3', 'relu4_3', 'relu3_2', 'relu2_2'])
        out = vgg_outputs(h_fc7, h_relu5_3, h_relu4_3, h_relu3_2, h_relu2_2)
        return out

class double_conv(nn.Module):
    def __init__(self, in_ch, mid_ch, out_ch):
        super(double_conv, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch + mid_ch, mid_ch, kernel_size=1),
            nn.BatchNorm2d(mid_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        x = self.conv(x)
        return x

class CRAFT(nn.Module):
    def __init__(self, pretrained=False, freeze=False):
        super(CRAFT, self).__init__()
        self.basenet = vgg16_bn(pretrained, freeze)
        self.upconv1 = double_conv(1024, 512, 256)
        self.upconv2 = double_conv(512, 256, 128)
        self.upconv3 = double_conv(256, 128, 64)
        self.upconv4 = double_conv(128, 64, 32)

        num_class = 2
        self.conv_cls = nn.Sequential(
            nn.Conv2d(32, 32, kernel_size=3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, kernel_size=3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(32, 16, kernel_size=3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(16, 16, kernel_size=1), nn.ReLU(inplace=True),
            nn.Conv2d(16, num_class, kernel_size=1),
        )

        init_weights(self.upconv1.modules())
        init_weights(self.upconv2.modules())
        init_weights(self.upconv3.modules())
        init_weights(self.upconv4.modules())
        init_weights(self.conv_cls.modules())

    def forward(self, x):
        sources = self.basenet(x)
        y = torch.cat([sources[0], sources[1]], dim=1)
        y = self.upconv1(y)
        y = F.interpolate(y, size=sources[2].size()[2:], mode='bilinear', align_corners=False)
        y = torch.cat([y, sources[2]], dim=1)
        y = self.upconv2(y)
        y = F.interpolate(y, size=sources[3].size()[2:], mode='bilinear', align_corners=False)
        y = torch.cat([y, sources[3]], dim=1)
        y = self.upconv3(y)
        y = F.interpolate(y, size=sources[4].size()[2:], mode='bilinear', align_corners=False)
        y = torch.cat([y, sources[4]], dim=1)
        feature = self.upconv4(y)
        y = self.conv_cls(feature)
        return y.permute(0,2,3,1), feature

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def loadImage(img_file):
    img = io.imread(img_file)
    if img.shape[0] == 2: 
        img = img[0]
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    if img.shape[2] == 4:
        img = img[:,:,:3]
    img = np.array(img)
    return img

def normalizeMeanVariance(in_img, mean=(0.485, 0.456, 0.406), variance=(0.229, 0.224, 0.225)):
    img = in_img.copy().astype(np.float32)
    img -= np.array([mean[0] * 255.0, mean[1] * 255.0, mean[2] * 255.0], dtype=np.float32)
    img /= np.array([variance[0] * 255.0, variance[1] * 255.0, variance[2] * 255.0], dtype=np.float32)
    return img

def copyStateDict(state_dict):
    if list(state_dict.keys())[0].startswith("module"):
        start_idx = 1
    else:
        start_idx = 0
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = ".".join(k.split(".")[start_idx:])
        new_state_dict[name] = v
    return new_state_dict

def detect(img, detector, device):
    x = [np.transpose(normalizeMeanVariance(img), (2, 0, 1))]
    x = torch.from_numpy(np.array(x))
    x = x.to(device)
    with torch.no_grad():
        y, feature = detector(x)
    d = y[0,:,:,0].cpu().data.numpy()
    return d

def gen_bounding_boxes(det, peaks):
    img = np.uint8(det * 255)
    _, img1 = cv2.threshold(img, 100, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(img1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    bounding_boxes = []
    
    # Handle case when no peaks are found
    if len(peaks) == 0:
        print("⚠️  No peaks found, using simple bounding boxes")
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            bounding_boxes.append((x, y, w, h))
        return bounding_boxes
    
    max_height = np.percentile(peaks[1:]-peaks[:-1], 80) if len(peaks) > 1 else det.shape[0] / 10
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h <= max_height:
            bounding_boxes.append((x, y, w, h))
        else:
            n_b = np.int32(np.ceil(h/max_height))
            equal_height = h // n_b
            height_adjustment = h - (equal_height * n_b)
            for i in range(n_b):
                new_y = y + (i * equal_height)
                box_height = equal_height + (height_adjustment if i == n_b - 1 else 0)
                bounding_boxes.append((x, new_y, w, box_height))
    
    return bounding_boxes

def assign_lines(bounding_boxes, det):
    ys = det.sum(axis=1)
    thres = 0.5 * ys.max()
    peaks, _ = find_peaks(ys, height=thres, distance=max(1, int(det.shape[0]/100)), width=5)
    
    # Handle case when no peaks are found
    if len(peaks) == 0:
        print("⚠️  No line peaks found, treating as single line")
        # Create a single pseudo-peak in the middle
        peaks = np.array([det.shape[0] // 2])
        return [0] * len(bounding_boxes), peaks
    
    xs = det.sum(axis=0)
    thres = 0.5 * xs.max()
    xpeaks, _ = find_peaks(xs, height=thres)
    
    if len(xpeaks) < 2:
        # Not enough x peaks, simple assignment
        lines = []
        for box in bounding_boxes:
            x, y, _, h = box
            mid_y = y + h / 2
            c_index = np.argmin(np.abs(peaks - mid_y))
            if(np.abs(mid_y-peaks[c_index])>20):
                c_index=-1
            lines.append(c_index)
        return lines, peaks
    
    # Find peaks at different x positions
    ys1 = det[:,xpeaks[0]:xpeaks[0]+100].sum(axis=1)
    thres = 0.5 * ys1.max()
    p1, _ = find_peaks(ys1, height=thres, distance=max(1, int(det.shape[0]/100)), width=5)
    
    ys2 = det[:,xpeaks[-1]-100:xpeaks[-1]].sum(axis=1)
    thres = 0.5 * ys2.max()
    p2, _ = find_peaks(ys2, height=thres, distance=max(1, int(det.shape[0]/100)), width=5)
    
    xmid = int((xpeaks[0]+xpeaks[-1])/2)
    ys3 = det[:,xmid-50:xmid+50].sum(axis=1)
    thres = 0.5 * ys3.max()
    p3, _ = find_peaks(ys3, height=thres, distance=max(1, int(det.shape[0]/100)), width=5)
    
    if(peaks[0]-p1[0]>det.shape[0]/12):
        p1 = np.copy(p1[1:])
    
    p = min(p1, p2, p3, key=len)
    l = len(p)
    
    if(len(p1)>=l+1):
        k = len(p1) - len(p)
        ind = np.argmin(np.abs(p1[:k+1] - p[0]))
        peaks1 = p1[ind:l+ind]
    else:
        peaks1 = p1

    if(len(p2)>=l+1):
        k = len(p2) - len(p)
        ind = np.argmin(np.abs(p2[:k+1] - p[0]))
        peaks2 = p2[ind:l+ind]
    else:
        peaks2 = p2

    if(len(p3)>=l+1):
        k = len(p3) - len(p)
        ind = np.argmin(np.abs(p3[:k+1] - p[0]))
        peaks3 = p3[ind:l+ind]
    else:
        peaks3 = p3

    lines = []
    for box in bounding_boxes:
        x, y, _, h = box
        mid_y = y + h / 2
        wt1 = np.abs(x - xpeaks[0])
        wt2 = np.abs(x - xpeaks[-1])
        wt3 = np.abs(x - xmid)
        if x<=xmid:
            peaks_interp = wt3*peaks1/(wt1+wt3)+wt1*peaks3/(wt1+wt3)
        else:
            peaks_interp = wt3*peaks2/(wt2+wt3)+wt2*peaks3/(wt2+wt3)
        
        c_index = np.argmin(np.abs(peaks_interp - mid_y))
        if(np.abs(mid_y-peaks_interp[c_index])>20):
            c_index=-1
        lines.append(c_index)
    
    return lines, peaks1

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

# Global model cache
_craft_model_cache = None
_craft_device_cache = None

def get_craft_model():
    """Get or initialize CRAFT model (singleton pattern)"""
    global _craft_model_cache, _craft_device_cache
    
    if _craft_model_cache is not None:
        return _craft_model_cache, _craft_device_cache
    
    # Check USE_GPU setting from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    use_gpu_env = os.getenv('USE_GPU', 'true').lower() == 'true'
    gpu_available = torch.cuda.is_available()
    
    # Use GPU only if both env says yes AND GPU is available
    if use_gpu_env and gpu_available:
        device = torch.device('cuda')
        print(f"Initializing CRAFT model on device: {device}")
    else:
        device = torch.device('cpu')
        if use_gpu_env and not gpu_available:
            print(f"⚠️  GPU requested but not available. Initializing CRAFT model on CPU")
        else:
            print(f"⚠️  Using CPU for CRAFT model (set USE_GPU=true for faster processing)")
    
    _detector = CRAFT()
    model_path = './char_visualisation/line-segmentation/pretrained_craft/craft_mlt_25k.pth'
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"CRAFT model not found at {model_path}. Please download it first.")
    
    # Force load on CPU first, then move to device
    _detector.load_state_dict(copyStateDict(torch.load(model_path, map_location='cpu')))
    
    # Only use DataParallel for GPU (it doesn't work with CPU)
    if device.type == 'cuda':
        detector = torch.nn.DataParallel(_detector).to(device)
    else:
        detector = _detector.to(device)
    
    detector.eval()
    
    _craft_model_cache = detector
    _craft_device_cache = device
    
    print("✓ CRAFT model loaded successfully!")
    return detector, device

def generate_visualization(image_path, output_dir):
    """
    Generate visualizations for the given image
    Returns: dict with paths to generated visualization images
    """
    print(f"\n{'='*60}")
    print(f"VISUALIZATION GENERATION STARTED")
    print(f"{'='*60}")
    print(f"Input Image: {image_path}")
    print(f"Output Dir: {output_dir}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    print(f"✓ Output directory created: {os.path.abspath(output_dir)}")
    
    try:
        # Get CRAFT model
        print("\n📦 Loading CRAFT model...")
        detector, device = get_craft_model()
        print(f"✓ CRAFT model loaded on device: {device}")
        
        # Load image
        print(f"\n📷 Loading image: {image_path}")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        original_image = loadImage(image_path)
        print(f"✓ Image loaded: {original_image.shape}")
        
        # Generate heatmap
        print("\n🔥 Generating character heatmap...")
        heatmap = detect(original_image, detector, device)
        print(f"✓ Heatmap generated: {heatmap.shape}")
        
        # Find peaks for line detection
        print("\n📊 Finding peaks for line detection...")
        ys = heatmap.sum(axis=1)
        thres = 0.5 * ys.max()
        peaks, _ = find_peaks(ys, height=thres, distance=max(1, int(heatmap.shape[0]/100)), width=5)
        print(f"✓ Found {len(peaks)} peaks")
        
        # Generate bounding boxes
        print("\n📦 Generating character bounding boxes...")
        bounding_boxes = gen_bounding_boxes(heatmap, peaks)
        print(f"✓ Generated {len(bounding_boxes)} bounding boxes")
        
        # Assign lines
        print("\n📝 Assigning characters to lines...")
        lines, line_peaks = assign_lines(bounding_boxes, heatmap)
        print(f"✓ Assigned to {len(line_peaks)} lines")
        
        # Resize original for display
        print("\n🖼️  Preparing display images...")
        display_img = cv2.resize(original_image, heatmap.shape[::-1], interpolation=cv2.INTER_CUBIC)
        display_img_gray = cv2.cvtColor(display_img, cv2.COLOR_RGB2GRAY)
        
        # Generate colors for lines
        colors = plt.cm.rainbow(np.linspace(0, 1, max(1, len(line_peaks))))
        print(f"✓ Display prepared")
        
        # ============================================================================
        # VISUALIZATION 1: Bounding Boxes
        # ============================================================================
        print("\n🎨 Creating Visualization 1: Bounding Boxes...")
        fig, ax = plt.subplots(figsize=(20, 10))
        ax.imshow(display_img_gray, cmap='gray')
        
        for (x, y, w, h), line_idx in zip(bounding_boxes, lines):
            if line_idx >= 0 and line_idx < len(colors):
                color = colors[line_idx]
                rect = Rectangle((x, y), w, h, linewidth=1.5, edgecolor=color, facecolor='none')
                ax.add_patch(rect)
        
        ax.set_title('Character Bounding Boxes', fontsize=16)
        ax.axis('off')
        plt.tight_layout()
        bbox_path = os.path.join(output_dir, 'bounding_boxes.png')
        plt.savefig(bbox_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Saved: {bbox_path}")
        
        # ============================================================================
        # VISUALIZATION 2: Heatmap
        # ============================================================================
        print("\n🎨 Creating Visualization 2: Heatmap...")
        fig, ax = plt.subplots(figsize=(20, 10))
        im = ax.imshow(heatmap, cmap='hot', interpolation='nearest')
        ax.set_title('Character Heatmap (CRAFT)', fontsize=16)
        ax.axis('off')
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        plt.tight_layout()
        heatmap_path = os.path.join(output_dir, 'heatmap.png')
        plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Saved: {heatmap_path}")
        
        # ============================================================================
        # VISUALIZATION 3: Line Segmentation
        # ============================================================================
        print("\n🎨 Creating Visualization 3: Line Segmentation...")
        fig, ax = plt.subplots(figsize=(20, 10))
        ax.imshow(display_img_gray, cmap='gray')
        
        for i, peak in enumerate(line_peaks):
            ax.axhline(y=peak, color='red', linestyle='--', linewidth=2, alpha=0.7)
            ax.text(10, peak, f'Line {i+1}', color='red', fontsize=12, 
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.set_title('Line Segmentation', fontsize=16)
        ax.axis('off')
        plt.tight_layout()
        lines_path = os.path.join(output_dir, 'line_segmentation.png')
        plt.savefig(lines_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Saved: {lines_path}")
        
        # ============================================================================
        # VISUALIZATION 4: Combined View
        # ============================================================================
        print("\n🎨 Creating Visualization 4: Combined Analysis...")
        fig = plt.figure(figsize=(24, 12))
        
        # Panel 1: Original with bounding boxes
        ax1 = plt.subplot(2, 2, 1)
        ax1.imshow(display_img_gray, cmap='gray')
        for (x, y, w, h), line_idx in zip(bounding_boxes, lines):
            if line_idx >= 0 and line_idx < len(colors):
                color = colors[line_idx]
                rect = Rectangle((x, y), w, h, linewidth=1, edgecolor=color, facecolor='none')
                ax1.add_patch(rect)
        ax1.set_title('Character Boxes', fontsize=12)
        ax1.axis('off')
        
        # Panel 2: Heatmap
        ax2 = plt.subplot(2, 2, 2)
        im2 = ax2.imshow(heatmap, cmap='hot', interpolation='nearest')
        ax2.set_title('CRAFT Heatmap', fontsize=12)
        ax2.axis('off')
        
        # Panel 3: Line segmentation
        ax3 = plt.subplot(2, 2, 3)
        ax3.imshow(display_img_gray, cmap='gray')
        for i, peak in enumerate(line_peaks):
            ax3.axhline(y=peak, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
        ax3.set_title('Line Segmentation', fontsize=12)
        ax3.axis('off')
        
        # Panel 4: Statistics
        ax4 = plt.subplot(2, 2, 4)
        ax4.axis('off')
        stats_text = f"""
DETECTION STATISTICS
════════════════════

Total Characters: {len(bounding_boxes)}
Total Lines: {len(line_peaks)}
Avg Chars/Line: {len(bounding_boxes)/max(1, len(line_peaks)):.1f}

Image Size: {heatmap.shape[1]} × {heatmap.shape[0]}
        """
        ax4.text(0.1, 0.5, stats_text, transform=ax4.transAxes, 
                 fontsize=14, verticalalignment='center', fontfamily='monospace',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        ax4.set_title('Statistics', fontsize=12)
        
        plt.suptitle('Character Detection Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        combined_path = os.path.join(output_dir, 'combined_analysis.png')
        plt.savefig(combined_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Saved: {combined_path}")
        
        print(f"\n{'='*60}")
        print("✓ ALL VISUALIZATIONS GENERATED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"📊 Statistics:")
        print(f"  • Total Characters: {len(bounding_boxes)}")
        print(f"  • Total Lines: {len(line_peaks)}")
        print(f"  • Avg Chars/Line: {len(bounding_boxes) / max(1, len(line_peaks)):.1f}")
        print(f"  • Image Size: {heatmap.shape[1]} × {heatmap.shape[0]}")
        print(f"\n📁 Output files:")
        print(f"  1. {os.path.basename(bbox_path)}")
        print(f"  2. {os.path.basename(heatmap_path)}")
        print(f"  3. {os.path.basename(lines_path)}")
        print(f"  4. {os.path.basename(combined_path)}")
        print(f"\n📂 Output directory: {os.path.abspath(output_dir)}")
        print(f"{'='*60}\n")
        
        return {
            'success': True,
            'stats': {
                'total_characters': len(bounding_boxes),
                'total_lines': len(line_peaks),
                'avg_chars_per_line': round(len(bounding_boxes) / max(1, len(line_peaks)), 1),
                'image_size': f"{heatmap.shape[1]} × {heatmap.shape[0]}"
            },
            'images': {
                'bounding_boxes': bbox_path,
                'heatmap': heatmap_path,
                'line_segmentation': lines_path,
                'combined_analysis': combined_path
            }
        }
    
    except Exception as e:
        print(f"\n{'='*60}")
        print("❌ ERROR GENERATING VISUALIZATION")
        print(f"{'='*60}")
        print(f"Error: {str(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        print(f"{'='*60}\n")
        return {
            'success': False,
            'error': str(e)
        }
