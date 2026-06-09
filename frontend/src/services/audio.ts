import { sendAudioChunk } from "./socket";

let audioContext: AudioContext | null = null;
let mediaStream: MediaStream | null = null;
let sourceNode: MediaStreamAudioSourceNode | null = null;
let workletNode: AudioWorkletNode | null = null;

export async function startAudioCapture() {
  if (audioContext) return;

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    // Request 16000Hz baseline. True sample rate will be logged empirically.
    audioContext = new AudioContext({ sampleRate: 16000 });
    console.log(
      `[Audio] Capture context initialized. System rate reported: ${audioContext.sampleRate}Hz`,
    );

    // Use window.location.origin to force an absolute path to the public directory
    const workletUrl = `${window.location.origin}/audio-worklet.js`;
    await audioContext.audioWorklet.addModule(workletUrl);

    sourceNode = audioContext.createMediaStreamSource(mediaStream);
    workletNode = new AudioWorkletNode(audioContext, "audio-capture-processor");

    workletNode.port.onmessage = (event) => {
      // Pipe raw binary packet directly into socket client
      sendAudioChunk(event.data);
    };

    sourceNode.connect(workletNode);

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
  if (audioContext) {
    audioContext.close().catch(() => {});
    audioContext = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }
  console.log("[Audio] Graph teardown complete. Capture stopped.");
}
