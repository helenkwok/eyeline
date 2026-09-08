#!/usr/bin/env python3
"""
Assemble the 2-minute Eyeline Demo Walkthrough Video.
Stitches high-resolution UI screenshots, live Veo 3.1 watermarked video clips,
and synchronized narration audio into a broadcast-ready 1080p 30fps MP4.
"""

import subprocess
import os

DEMO_DIR = "/Users/helen/workspace/eyeline/docs/demo"
AUDIO_DIR = os.path.join(DEMO_DIR, "audio")
OUTPUT_VIDEO = os.path.join(DEMO_DIR, "eyeline_walkthrough.mp4")

def get_duration(audio_file):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_file
    ]
    res = subprocess.check_output(cmd).decode().strip()
    return float(res)

def make_slide(image_path, audio_path, output_path, padding_end=1.0):
    dur = get_duration(audio_path) + padding_end
    # Scale image to 1920x1080 with padding, 30fps, H.264
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{dur:.2f}",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
        "-r", "30",
        output_path
    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Rendered {output_path} (duration: {dur:.2f}s)")

def make_veo_scene(modal_img, veo_video, audio_path, output_path):
    # Scene 4 splits audio between the modal preview and the live Veo video
    total_dur = get_duration(audio_path) + 1.0
    half_dur = total_dur / 2.0

    # Part A: Modal image with first half of audio
    part_a_audio = os.path.join(AUDIO_DIR, "part4_a.wav")
    part_b_audio = os.path.join(AUDIO_DIR, "part4_b.wav")
    subprocess.check_call([
        "ffmpeg", "-y", "-i", audio_path,
        "-t", f"{half_dur:.2f}", "-c", "copy", part_a_audio
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call([
        "ffmpeg", "-y", "-ss", f"{half_dur:.2f}", "-i", audio_path,
        "-c", "copy", part_b_audio
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    dur_a = get_duration(part_a_audio)
    dur_b = get_duration(part_b_audio) + 1.0

    part_a_mp4 = os.path.join(DEMO_DIR, "scene4_a.mp4")
    part_b_mp4 = os.path.join(DEMO_DIR, "scene4_b.mp4")

    # Render Part A: Modal screenshot
    cmd_a = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", modal_img,
        "-i", part_a_audio,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{dur_a:.2f}",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
        "-r", "30",
        part_a_mp4
    ]
    subprocess.check_call(cmd_a, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Render Part B: Live Veo video looped to match dur_b
    cmd_b = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", veo_video,
        "-i", part_b_audio,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{dur_b:.2f}",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
        "-r", "30",
        part_b_mp4
    ]
    subprocess.check_call(cmd_b, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Concat Part A and Part B
    concat_list = os.path.join(DEMO_DIR, "scene4_concat.txt")
    with open(concat_list, "w") as f:
        f.write(f"file '{part_a_mp4}'\nfile '{part_b_mp4}'\n")

    subprocess.check_call([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list, "-c", "copy", output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Rendered {output_path} (Veo Scene, total duration: {total_dur:.2f}s)")

def make_scene3(control_img, receipts_img, audio_path, output_path):
    total_dur = get_duration(audio_path) + 1.0
    half_dur = total_dur / 2.0

    part_a_audio = os.path.join(AUDIO_DIR, "part3_a.wav")
    part_b_audio = os.path.join(AUDIO_DIR, "part3_b.wav")
    subprocess.check_call([
        "ffmpeg", "-y", "-i", audio_path,
        "-t", f"{half_dur:.2f}", "-c", "copy", part_a_audio
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call([
        "ffmpeg", "-y", "-ss", f"{half_dur:.2f}", "-i", audio_path,
        "-c", "copy", part_b_audio
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    dur_a = get_duration(part_a_audio)
    dur_b = get_duration(part_b_audio) + 1.0

    part_a_mp4 = os.path.join(DEMO_DIR, "scene3_a.mp4")
    part_b_mp4 = os.path.join(DEMO_DIR, "scene3_b.mp4")

    subprocess.check_call([
        "ffmpeg", "-y", "-loop", "1", "-i", control_img, "-i", part_a_audio,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", f"{dur_a:.2f}",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
        "-r", "30", part_a_mp4
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.check_call([
        "ffmpeg", "-y", "-loop", "1", "-i", receipts_img, "-i", part_b_audio,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", f"{dur_b:.2f}",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
        "-r", "30", part_b_mp4
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    concat_list = os.path.join(DEMO_DIR, "scene3_concat.txt")
    with open(concat_list, "w") as f:
        f.write(f"file '{part_a_mp4}'\nfile '{part_b_mp4}'\n")

    subprocess.check_call([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list, "-c", "copy", output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Rendered {output_path} (Scene 3, total duration: {total_dur:.2f}s)")

def main():
    print("=== Assembling Eyeline Demo Walkthrough Video ===")

    scene1_mp4 = os.path.join(DEMO_DIR, "scene1.mp4")
    scene2_mp4 = os.path.join(DEMO_DIR, "scene2.mp4")
    scene3_mp4 = os.path.join(DEMO_DIR, "scene3.mp4")
    scene4_mp4 = os.path.join(DEMO_DIR, "scene4.mp4")
    scene5_mp4 = os.path.join(DEMO_DIR, "scene5.mp4")

    # Scene 1: Overview & Problem
    make_slide(
        os.path.join(DEMO_DIR, "05_station_overview.png"),
        os.path.join(AUDIO_DIR, "part1.wav"),
        scene1_mp4
    )

    # Scene 2: Pillar 1 Classical CV
    make_slide(
        os.path.join(DEMO_DIR, "01_judge_defect.png"),
        os.path.join(AUDIO_DIR, "part2.wav"),
        scene2_mp4
    )

    # Scene 3: Pillar 2 Gemini Adjudication
    make_scene3(
        os.path.join(DEMO_DIR, "02_judge_control.png"),
        os.path.join(DEMO_DIR, "04_judge_receipts.png"),
        os.path.join(AUDIO_DIR, "part3.wav"),
        scene3_mp4
    )

    # Scene 4: Pillar 3 Veo 3.1 Generative Cutaway
    make_veo_scene(
        os.path.join(DEMO_DIR, "06_veo_modal.png"),
        "/Users/helen/workspace/eyeline/ui/assets/veo_pickup_clock.mp4",
        os.path.join(AUDIO_DIR, "part4.wav"),
        scene4_mp4
    )

    # Scene 5: IBM Bob Provenance & Verifiable Receipts
    make_slide(
        os.path.join(DEMO_DIR, "04_judge_receipts.png"),
        os.path.join(AUDIO_DIR, "part5.wav"),
        scene5_mp4
    )

    # Final Concat
    final_concat = os.path.join(DEMO_DIR, "final_concat.txt")
    with open(final_concat, "w") as f:
        f.write(f"file '{scene1_mp4}'\n")
        f.write(f"file '{scene2_mp4}'\n")
        f.write(f"file '{scene3_mp4}'\n")
        f.write(f"file '{scene4_mp4}'\n")
        f.write(f"file '{scene5_mp4}'\n")

    subprocess.check_call([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", final_concat, "-c", "copy", OUTPUT_VIDEO
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    dur = get_duration(OUTPUT_VIDEO)
    print(f"SUCCESS: Assembled {OUTPUT_VIDEO}")
    print(f"Total Video Duration: {dur:.2f} seconds ({dur/60:.1f} minutes)")

if __name__ == "__main__":
    main()
