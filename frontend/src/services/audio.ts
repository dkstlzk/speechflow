import { sendAudioChunk } from "./socket";

let audioContext: AudioContext | null = null;
let mediaStream: MediaStream | null = null;
let sourceNode: MediaStreamAudioSourceNode | null = null;
let micStream: MediaStream | null = null;
let micSourceNode: MediaStreamAudioSourceNode | null = null;
let workletNode: AudioWorkletNode | null = null;

export function initAudioContext(): number {
  if (!audioContext) {
    audioContext = new AudioContext({ sampleRate: 16000 });
  }
  return audioContext.sampleRate;
}

export async function startAudioCapture(
  captureSystem: boolean = false,
  onStreamEnded?: () => void,
): Promise<void> {
  if (!audioContext) {
    initAudioContext();
  }

  if (!navigator.mediaDevices) {
    throw new Error("Your browser does not support media devices.");
  }
  if (captureSystem && !navigator.mediaDevices.getDisplayMedia) {
    throw new Error("System audio capture requires Chrome/Edge.");
  }
  if (typeof AudioWorkletNode === "undefined") {
    throw new Error(
      "Your browser does not support AudioWorklets. Please update to a modern browser.",
    );
  }

  try {
    if (captureSystem) {
      mediaStream = await navigator.mediaDevices.getDisplayMedia({
        audio: true,
        video: true, // required by some browsers, but we will ignore it
      });
      // Also capture the microphone to mix the local user's voice
      micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } else {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    }

    if (onStreamEnded) {
      let endedFired = false;
      mediaStream.getTracks().forEach((track) => {
        track.onended = () => {
          console.log(`[Audio] Track ${track.kind} ended externally.`);
          if (!endedFired) {
            endedFired = true;
            onStreamEnded();
          }
        };
      });
    }

    if (!audioContext) {
      throw new Error("Failed to initialize AudioContext");
    }

    // Use the initialized context
    console.log(
      `[Audio] Capture context initialized. System rate reported: ${audioContext.sampleRate}Hz`,
    );

    // Use window.location.origin to force an absolute path to the public directory
    const workletUrl = `${window.location.origin}/audio-worklet.js`;
    await audioContext.audioWorklet.addModule(workletUrl);

    sourceNode = audioContext.createMediaStreamSource(mediaStream);
    if (micStream) {
      micSourceNode = audioContext.createMediaStreamSource(micStream);
    }
    workletNode = new AudioWorkletNode(audioContext, "audio-capture-processor");

    workletNode.port.onmessage = (event) => {
      // Pipe raw binary packet directly into socket client
      sendAudioChunk(event.data);
    };

    sourceNode.connect(workletNode);
    if (micSourceNode) {
      micSourceNode.connect(workletNode);
    }

    // Connect worklet to destination via a muted gain node to prevent browser GC
    const gainNode = audioContext.createGain();
    gainNode.gain.value = 0;
    gainNode.channelCount = 1;
    workletNode.connect(gainNode);
    gainNode.connect(audioContext.destination);

    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }

    // Bind global lifecycle hook for developer environment sanity
    window.addEventListener("beforeunload", stopAudioCapture);
  } catch (err) {
    console.error("[Audio] Failed to initialize hardware capture graph:", err);
    stopAudioCapture();
  }
}

export function stopAudioCapture() {
  window.removeEventListener("beforeunload", stopAudioCapture);

  if (workletNode) {
    workletNode.disconnect();
    workletNode = null;
  }
  if (sourceNode) {
    sourceNode.disconnect();
    sourceNode = null;
  }
  if (micSourceNode) {
    micSourceNode.disconnect();
    micSourceNode = null;
  }
  if (audioContext) {
    audioContext.close().catch(() => {});
    audioContext = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }
  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop());
    micStream = null;
  }
  console.log("[Audio] Graph teardown complete. Capture stopped.");
}
