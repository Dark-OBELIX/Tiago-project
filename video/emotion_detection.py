import cv2
import json
import random
import time
from collections import Counter

from deepface import DeepFace

# ----------------------------
# 1) Citations (4 par émotion)
# ----------------------------
QUOTES = {
    "happy": [
        "Je détecte que vous êtes joyeux, n'oubliez pas que la joie est un signe discret que tu avances dans la bonne direction.",
        "Je détecte que vous êtes joyeux, n'oubliez pas que quand la joie passe, laisse-la te rappeler ce qui compte vraiment.",
        "Je détecte que vous êtes joyeux, n'oubliez pas que la joie n’efface pas le reste : elle l’éclaire.",
        "Je détecte que vous êtes joyeux, n'oubliez pas de garder cette joie comme une boussole, pas comme une destination.",
    ],
    "sad": [
        "Je détecte que vous êtes triste, n'oubliez pas que la tristesse n’est pas un échec : c’est une profondeur qui parle.",
        "Je détecte que vous êtes triste, n'oubliez pas que parfois, le cœur ralentit pour comprendre.",
        "Je détecte que vous êtes triste, n'oubliez pas que la tristesse est un passage, pas une identité.",
        "Je détecte que vous êtes triste, n'oubliez pas que même la pluie a une utilité : elle prépare le sol.",
    ],
    "angry": [
        "Je détecte que vous êtes en colère, n'oubliez pas que la colère est une énergie : à vous de choisir où elle va.",
        "Je détecte que vous êtes en colère, n'oubliez pas que la colère éclaire un besoin, mais ne donne pas toujours la solution.",
        "Je détecte que vous êtes en colère, n'oubliez pas que respirer, c’est reprendre le contrôle.",
        "Je détecte que vous êtes en colère, n'oubliez pas que la colère est un feu : apprivoisé, il réchauffe; lâché, il brûle.",
    ],
    "neutral": [
        "Je ne détecte pas d'émotion particulière chez vous, n'oubliez pas que le calme est une forme de force : rien à prouver, tout à construire.",
        "Je ne détecte pas d'émotion particulière chez vous, n'oubliez pas que la neutralité, c’est parfois l’équilibre retrouvé.",
        "Je ne détecte pas d'émotion particulière chez vous, n'oubliez pas que dans le silence, on entend mieux l’essentiel.",
        "Je ne détecte pas d'émotion particulière chez vous, n'oubliez pas que la stabilité, c’est un point d’appui pour la suite.",
    ],
}

ALLOWED = ["angry", "happy", "sad", "neutral"]

# ---------------------------------------
# 2) Paramètres : durée et échantillonnage
# ---------------------------------------
CAPTURE_SECONDS = 3.0     # laps de temps court
ANALYZE_EVERY_N_FRAMES = 5  # analyse toutes les N frames (réduit CPU)
CAMERA_INDEX = 0

# ---------------------------------------
# 3) Détection visage (léger) + DeepFace
# ---------------------------------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def pick_quote(emotion: str) -> str:
    # fallback sécurité
    if emotion not in QUOTES:
        emotion = "neutral"
    return random.choice(QUOTES[emotion])

def normalize_emotion(raw_emotions: dict) -> str:
    """Garde uniquement ALLOWED + applique un mini-ajustement si tu veux."""
    filtered = {k: raw_emotions.get(k, 0.0) for k in ALLOWED}

    boost = {
        "angry": 10.0, #boost angry
        "sad": 1.0,
        "happy": 1.0,
        "neutral": 0.75 #nerf neutral
    }
    adjusted = {emo: filtered[emo] * boost.get(emo, 1.0) for emo in filtered}
    return max(adjusted, key=adjusted.get)

def build_tts_json(text: str) -> dict:
    """Format JSON 'action + texte' comme tu l'as décrit."""
    return {
        "action": "text-to-speech",
        "text": text
    }

def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        # JSON d'erreur (pratique pour l'intégration)
        print(json.dumps({"action": "text-to-speech", "text": "Je n'arrive pas à accéder à la caméra."}, ensure_ascii=False))
        return

    emotions_detected = []
    frame_count = 0

    start = time.time()
    while (time.time() - start) < CAPTURE_SECONDS:
        ret, frame = cap.read()
        if not ret:
            continue

        frame_count += 1
        if frame_count % ANALYZE_EVERY_N_FRAMES != 0:
            continue

        # Prétraitement rapide
        frame = cv2.resize(frame, (960, 540))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) == 0:
            continue

        # Prend le 1er visage détecté
        (x, y, w, h) = faces[0]
        margin = 20
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(frame.shape[1], x + w + margin)
        y2 = min(frame.shape[0], y + h + margin)
        face = frame[y1:y2, x1:x2]

        # Analyse DeepFace
        try:
            result = DeepFace.analyze(
                face,
                actions=["emotion"],
                enforce_detection=False
            )
            raw_emotions = result[0]["emotion"]
            emo = normalize_emotion(raw_emotions)
            emotions_detected.append(emo)
        except Exception:
            # si DeepFace rate une frame, on ignore
            continue

    cap.release()

    # ---------------------------------------
    # 4) Décision finale (vote majoritaire)
    # ---------------------------------------
    if len(emotions_detected) == 0:
        final_emotion = "neutral"
    else:
        final_emotion = Counter(emotions_detected).most_common(1)[0][0]

    quote = pick_quote(final_emotion)

    # ---------------------------------------
    # 5) Sortie JSON puis stop
    # ---------------------------------------
    payload = build_tts_json(quote)
    print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    main()
