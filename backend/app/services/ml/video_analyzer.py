"""
Video Analyzer - analyzes video frames for eye contact, posture, fidgeting.
Uses MediaPipe Face Mesh for face landmarks.

Note: This runs on the CLIENT side (browser) using MediaPipe.js.
This file provides the analysis logic that the frontend will use.
"""


class VideoAnalyzer:
    """
    Server-side video analysis logic.
    In practice, most of this runs on the client (JavaScript + MediaPipe.js).
    This class provides the scoring/thresholding logic.
    """

    @staticmethod
    def calculate_eye_contact_score(face_landmarks: dict) -> float:
        """
        Calculate eye contact score from face landmarks.

        Args:
            face_landmarks: Dict with eye positions, head rotation
                {
                    "left_eye": {"x": float, "y": float},
                    "right_eye": {"x": float, "y": float},
                    "nose": {"x": float, "y": float},
                    "head_yaw": float,   # horizontal rotation (-90 to 90)
                    "head_pitch": float  # vertical rotation (-90 to 90)
                }

        Returns:
            Score 0-1 (1 = perfect eye contact)
        """
        # Good eye contact: head facing camera (yaw/pitch near 0)
        yaw = abs(face_landmarks.get("head_yaw", 0))
        pitch = abs(face_landmarks.get("head_pitch", 0))

        # Thresholds
        # Perfect: yaw < 15°, pitch < 15°
        # Poor: yaw > 45°, pitch > 30°

        yaw_score = max(0, 1 - (yaw / 45))
        pitch_score = max(0, 1 - (pitch / 30))

        return (yaw_score + pitch_score) / 2

    @staticmethod
    def detect_fidgeting(movement_history: list) -> dict:
        """
        Detect fidgeting from body movement history.

        Args:
            movement_history: List of movement magnitudes over time
                [0.1, 0.05, 0.3, 0.02, ...] (0 = still, 1 = large movement)

        Returns:
            {
                "fidgeting_count": int,
                "avg_movement": float,
                "still_percentage": float
            }
        """
        if not movement_history:
            return {
                "fidgeting_count": 0,
                "avg_movement": 0.0,
                "still_percentage": 100.0
            }

        # Count sudden movements (spikes > 0.2)
        fidget_threshold = 0.2
        fidgets = sum(1 for m in movement_history if m > fidget_threshold)

        avg_movement = sum(movement_history) / len(movement_history)
        still_frames = sum(1 for m in movement_history if m < 0.05)
        still_percentage = (still_frames / len(movement_history)) * 100

        return {
            "fidgeting_count":   fidgets,
            "avg_movement":      round(avg_movement, 3),
            "still_percentage":  round(still_percentage, 1)
        }

    @staticmethod
    def calculate_posture_score(shoulder_landmarks: dict) -> float:
        """
        Calculate posture score from shoulder positions.

        Args:
            shoulder_landmarks: {
                "left_shoulder": {"x": float, "y": float},
                "right_shoulder": {"x": float, "y": float}
            }

        Returns:
            Score 0-1 (1 = perfect posture)
        """
        left = shoulder_landmarks.get("left_shoulder", {"y": 0})
        right = shoulder_landmarks.get("right_shoulder", {"y": 0})

        # Good posture: shoulders level (similar y values)
        y_diff = abs(left["y"] - right["y"])

        # Perfect: y_diff < 0.02 (2% of frame)
        # Poor: y_diff > 0.1 (10% of frame)
        score = max(0, 1 - (y_diff / 0.1))

        return score


# ── Client-side JavaScript code (for reference) ───────────────────────────────
"""
This is what the frontend should implement using MediaPipe.js:

// In the interview page, add MediaPipe Face Mesh
import { FaceMesh } from '@mediapipe/face_mesh';

const faceMesh = new FaceMesh({
  locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
});

faceMesh.setOptions({
  maxNumFaces: 1,
  refineLandmarks: true,
  minDetectionConfidence: 0.5,
  minTrackingConfidence: 0.5
});

faceMesh.onResults(async (results) => {
  if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
    return;
  }

  const landmarks = results.multiFaceLandmarks[0];

  // Extract key points
  const leftEye = landmarks[159];   // left eye center
  const rightEye = landmarks[386];  // right eye center
  const nose = landmarks[1];        // nose tip

  // Calculate head rotation (simplified)
  const headYaw = calculateYaw(leftEye, rightEye);
  const headPitch = calculatePitch(nose, leftEye);

  // Calculate eye contact score
  const eyeContactScore = calculateEyeContact(headYaw, headPitch);

  // Send to server
  ws.send(JSON.stringify({
    type: "video_metrics",
    eye_contact: eyeContactScore,
    fidgeting: detectMovement(landmarks, previousLandmarks)
  }));

  previousLandmarks = landmarks;
});

// Process video frames
async function processFrame() {
  if (videoElement.readyState === 4) {
    await faceMesh.send({ image: videoElement });
  }
  requestAnimationFrame(processFrame);
}

processFrame();
"""