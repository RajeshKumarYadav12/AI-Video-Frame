import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import random
import os
import tempfile

def apply_scribbles(img, intensity=5):
    """Add random colorful scribbles to the image"""
    draw = ImageDraw.Draw(img, 'RGBA')
    width, height = img.size
    colors = [(255, 0, 0, 180), (0, 255, 255, 180), (255, 255, 0, 180), 
              (0, 255, 0, 180), (255, 0, 255, 180), (255, 128, 0, 180),
              (128, 0, 255, 180), (255, 192, 203, 180)]
    
    num_scribbles = random.randint(intensity, intensity * 2)
    for _ in range(num_scribbles):
        # Create curved scribbles
        points = [(random.randint(0, width), random.randint(0, height)) 
                  for _ in range(random.randint(5, 12))]
        draw.line(points, fill=random.choice(colors), width=random.randint(3, 8))
        
        # Add some dots/circles
        if random.random() > 0.5:
            x, y = random.randint(0, width), random.randint(0, height)
            r = random.randint(5, 15)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=random.choice(colors))
    
    return img

def create_paper_texture(size, seed):
    """Create a procedural paper texture"""
    width, height = size
    # Create base texture
    np.random.seed(seed)
    noise = np.random.randint(220, 245, (height, width, 3), dtype=np.uint8)
    
    # Add some variation
    paper = Image.fromarray(noise, 'RGB')
    paper = paper.filter(ImageFilter.GaussianBlur(1))
    
    # Add some aging effect
    alpha = Image.new('L', size, 200)
    paper_rgba = paper.convert('RGBA')
    paper_rgba.putalpha(alpha)
    
    return paper_rgba
  
def apply_paper_frame(img, frame_count, use_texture=True):
    """Apply a paper frame overlay that changes over time"""
    if not use_texture:
        return img
    
    # Change texture seed every 10 frames
    seed = frame_count // 10
    paper = create_paper_texture(img.size, seed)
    
    # Blend the paper texture with the image
    img_rgba = img.convert("RGBA")
    result = Image.blend(img_rgba, paper, alpha=0.3)
    
    return result

st.set_page_config(page_title="Scrapbook Video Creator", layout="wide")
st.title("🎨 Scrapbook Video Creator")
st.markdown("Apply scribbles and paper texture effects to your videos!")

# Sidebar for controls
st.sidebar.header("⚙️ Settings")

# Option to use default video or upload
use_default = st.sidebar.checkbox("Use default video (skate_input)", value=True)

video_path = None
if use_default:
    default_video = "Copy of skate_input CLEAREST EXAMPLE__ START HERE.mp4"
    if os.path.exists(default_video):
        video_path = default_video
        st.sidebar.success(f"✓ Using: {default_video[:30]}...")
    else:
        st.sidebar.error("Default video not found!")
else:
    uploaded_video = st.sidebar.file_uploader("Upload a video file", type=["mp4", "mov", "avi"])
    if uploaded_video:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded_video.read())
        tfile.close()
        video_path = tfile.name
        st.sidebar.success("✓ Video uploaded!")

# Effect controls
st.sidebar.subheader("🎨 Effect Settings")
duration = st.sidebar.slider("Video duration (seconds)", 1, 30, 5, help="Process first N seconds of video")
scribble_intensity = st.sidebar.slider("Scribble intensity", 1, 10, 5)
enable_scribbles = st.sidebar.checkbox("Enable scribbles", value=True)
enable_paper = st.sidebar.checkbox("Enable paper texture", value=True)

if video_path:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📹 Input Video")
        st.video(video_path)
    
    if st.sidebar.button("🎬 Process Video", type="primary"):
        with col2:
            st.subheader("✨ Output Video")
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            cap = cv2.VideoCapture(video_path)
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            status_text.info(f"📊 Video info: {width}x{height} @ {fps}fps, Total frames: {total_frames}")
            
            output_path = "output_scrapbook.avi"
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            frame_count = 0
            max_frames = min(fps * duration, total_frames)
            
            while cap.isOpened() and frame_count < max_frames:
                ret, frame = cap.read()
                if not ret: 
                    break
                
                # Convert to PIL for processing
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb).convert('RGB')
                
                # Apply effects
                if enable_scribbles:
                    pil_img = apply_scribbles(pil_img, scribble_intensity)
                
                if enable_paper:
                    pil_img = apply_paper_frame(pil_img, frame_count, True)
                
                # Convert back to BGR for video output
                final_array = np.array(pil_img.convert('RGB'))
                final_frame = cv2.cvtColor(final_array, cv2.COLOR_RGB2BGR)
                out.write(final_frame)
                
                frame_count += 1
                progress = frame_count / max_frames
                progress_bar.progress(progress)
                
                if frame_count % 30 == 0:
                    status_text.info(f"⏳ Processing frame {frame_count}/{max_frames}...")
            
            cap.release()
            out.release()
            
            # Convert to web-compatible format
            status_text.info("🔄 Converting video for web playback...")
            final_output = "output_scrapbook_web.mp4"
            
            # Try using ffmpeg for better compatibility
            try:
                import subprocess
                subprocess.run([
                    'ffmpeg', '-y', '-i', output_path,
                    '-c:v', 'libx264', '-preset', 'fast',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    final_output
                ], check=True, capture_output=True)
                output_path = final_output
                status_text.success(f"✅ Video processing complete! Processed {frame_count} frames.")
            except:
                # If ffmpeg fails, try reopening and rewriting with different codec
                cap_temp = cv2.VideoCapture(output_path)
                fourcc_web = cv2.VideoWriter_fourcc(*'avc1')
                out_web = cv2.VideoWriter(final_output, fourcc_web, fps, (width, height))
                
                while cap_temp.isOpened():
                    ret, frame = cap_temp.read()
                    if not ret:
                        break
                    out_web.write(frame)
                
                cap_temp.release()
                out_web.release()
                output_path = final_output
                status_text.success(f"✅ Video processing complete! Processed {frame_count} frames.")
            st.video(output_path)
            
            # Download button
            with open(output_path, 'rb') as f:
                st.download_button(
                    label="📥 Download Output Video",
                    data=f,
                    file_name="scrapbook_output.mp4",
                    mime="video/mp4"
                )
else:
    st.info("👈 Please select or upload a video to get started!")





