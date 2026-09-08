#!/usr/bin/env bash
set -e

mkdir -p docs/demo/audio

say -v Samantha -r 170 -o docs/demo/audio/part1.aiff \
"In film production, script supervisors have just two minutes between takes to catch physical continuity breaks before the set is struck. Once struck, a missed prop or wardrobe error costs tens of thousands of dollars to reshoot. Eyeline is an autonomous continuity copilot built under the strict Agentic Cinema Hackathon guidelines."

say -v Samantha -r 170 -o docs/demo/audio/part2.aiff \
"Pillar 1 performs sub-pixel perspective alignment and exposure normalization using classical computer vision. Within 80 milliseconds, it flags physical changes like this mug fill level jump, isolating candidate bounding boxes with zero external deep learning object detectors, fully compliant with Rule 7.B."

say -v Samantha -r 170 -o docs/demo/audio/part3.aiff \
"Classical CV alone flags intentional lighting shifts and camera angle adjustments. In Pillar 2, an agent powered by Gemini 3.8 Flash inspects the candidate crops against scene context. On our 16 negative control pairs, Gemini retracted four of seven false alarms with zero regressions, cutting the false alarm rate to 18.8 percent while preserving 100 percent of defect detections."

say -v Samantha -r 170 -o docs/demo/audio/part4.aiff \
"When a continuity break is discovered after wrap and the set has already been struck, Eyeline invokes Pillar 3: Google Cloud Veo 3.1. It synthesizes a cinematic macro cutaway insert, stamped with a mandatory synthetic disclosure watermark, allowing editorial to bridge the scene transition without an emergency reshoot."

say -v Samantha -r 170 -o docs/demo/audio/part5.aiff \
"All modular code components were authored by IBM Bob with complete transcript provenance. All 32 benchmark pairs, evaluation fixtures, and interactive review stations run completely offline with zero credentials. Try the live station today."

# Convert AIFF to WAV / AAC and check durations
for i in 1 2 3 4 5; do
  ffmpeg -y -i "docs/demo/audio/part$i.aiff" "docs/demo/audio/part$i.wav" 2>/dev/null
  echo "Part $i duration:"
  ffprobe -i "docs/demo/audio/part$i.wav" -show_entries format=duration -v quiet -of csv="p=0"
done
