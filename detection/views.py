import os
import cv2
import numpy as np
from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
from django.core.files.storage import FileSystemStorage
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# Load YOLO model
MODEL_PATH = "weights/best.pt"  # Ensure the correct path
model = YOLO(MODEL_PATH)

# Initialize DeepSORT tracker with appropriate parameters
tracker = DeepSort(max_age=30, n_init=3, max_iou_distance=0.7)

# Global variables for storing video path and bicycle tracking
VIDEO_PATH = None
bicycle_ids = set()  # Stores unique bicycle IDs

# Constants for calculations
FUEL_COST_SAVED = 112  # PHP per bicycle
CALORIES_BURNED = 317  # kcal per bicycle
CARBON_REDUCTION = 3.74  # kg CO2 per bicycle


def upload_video(request):
    """Handles video upload and renders the detection page."""
    global VIDEO_PATH, bicycle_ids
    # Always refresh the count on page load
    bicycle_ids = set()

    if request.method == "POST" and request.FILES.get("video"):
        video = request.FILES["video"]
        fs = FileSystemStorage()
        video_filename = fs.save(video.name, video)
        VIDEO_PATH = fs.path(video_filename)
        # Reset bicycle IDs for a new video
        bicycle_ids = set()
        return render(
            request,
            "detection/index.html",
            {"video_url": VIDEO_PATH},
        )
    return render(request, "detection/index.html")


def video_feed(request):
    """Streams video frames with live bicycle detection and tracking (2x Faster)."""
    global VIDEO_PATH, bicycle_ids

    if not VIDEO_PATH:
        return StreamingHttpResponse("No video uploaded.", content_type="text/plain")

    def generate():
        cap = cv2.VideoCapture(VIDEO_PATH)
        frame_skip = 2  # Process every 2nd frame
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % frame_skip != 0:  # Skip every 2nd frame
                continue

            # Run YOLO model (fast inference)
            results = model.predict(frame, verbose=False)
            detections = []

            for result in results:
                boxes = result.boxes.xyxy.cpu().numpy()
                confidences = result.boxes.conf.cpu().numpy()
                class_ids = result.boxes.cls.cpu().numpy().astype(int)

                for box, conf, class_id in zip(boxes, confidences, class_ids):
                    if class_id == 0 and conf > 0.60:  # Only bicycles
                        x1, y1, x2, y2 = map(int, box)
                        detections.append(([x1, y1, x2, y2], conf, class_id))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Update tracker
            tracked_objects = tracker.update_tracks(detections, frame=frame)

            for track in tracked_objects:
                if track.is_confirmed() and track.track_id is not None:
                    bicycle_ids.add(track.track_id)

                    ltrb = track.to_ltwh()
                    x1, y1, w, h = map(int, ltrb)
                    x2, y2 = x1 + w, y1 + h

                    cv2.putText(
                        frame,
                        f"ID {track.track_id}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        2,
                    )

            # Calculate stats
            num_bicycles = len(bicycle_ids)
            total_fuel_saved = num_bicycles * FUEL_COST_SAVED
            total_calories = num_bicycles * CALORIES_BURNED
            total_carbon_reduction = num_bicycles * CARBON_REDUCTION

            # Display statistics with up to 2 decimals
            cv2.putText(
                frame,
                f"Bicycle Count: {num_bicycles}",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                f"Fuel Saved: PHP {total_fuel_saved:.2f}",
                (30, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                f"Calories Burned: {total_calories:.2f} kcal",
                (30, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                f"Carbon Reduction: {total_carbon_reduction:.2f} kg",
                (30, 140),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

            # Encode frame with optimized compression
            ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )

        cap.release()

    return StreamingHttpResponse(
        generate(), content_type="multipart/x-mixed-replace; boundary=frame"
    )


def get_bike_count(request):
    """Returns the current bicycle count and statistics as JSON."""
    global bicycle_ids

    num_bicycles = len(bicycle_ids)
    total_fuel_saved = round(num_bicycles * FUEL_COST_SAVED, 2)
    total_calories = round(num_bicycles * CALORIES_BURNED, 2)
    total_carbon_reduction = round(num_bicycles * CARBON_REDUCTION, 2)

    return JsonResponse(
        {
            "count": num_bicycles,
            "fuel_saved": total_fuel_saved,
            "calories_burned": total_calories,
            "carbon_reduction": total_carbon_reduction,
        }
    )
