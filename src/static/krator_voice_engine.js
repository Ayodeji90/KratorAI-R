/**
 * KratorAI Voice Engine
 * 
 * A reusable Class to handle Realtime Audio Streaming (PCM16, 24kHz)
 * for Business Onboarding and Design Editing.
 */
class KratorVoiceEngine {
    constructor(options = {}) {
        this.wsUrl = options.wsUrl || '';
        this.onStatusChange = options.onStatusChange || (() => { });
        this.onMessage = options.onMessage || (() => { });
        this.onComplete = options.onComplete || (() => { });
        this.onUpdate = options.onUpdate || (() => { }); // Added for Spec v2 real-time state

        this.ws = null;
        this.audioStream = null;
        this.audioContext = null;
        this.isActive = false;
        this.isMicMuted = false;
        this.isResponseDone = false;
        this.isPlayingQueue = false;
        this.audioQueue = [];
        this.nextPlayTime = 0;
    }

    async start() {
        if (!this.wsUrl) throw new Error("WebSocket URL is required");
        this.setStatus('Connecting...', 'idle');

        try {
            // 1. Get Microphone Access (24kHz PCM)
            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 24000 }
            });

            // 2. Initialize Audio Context
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });

            // 3. Connect WebSocket
            this.ws = new WebSocket(this.wsUrl);
            this.isActive = true;

            this.ws.onopen = () => {
                this.setStatus('Connected! Speak anytime...', 'listening');
                this.startStreaming();
            };

            this.ws.onmessage = async (event) => {
                const data = JSON.parse(event.data);
                await this.handleEvent(data);
            };

            this.ws.onerror = (err) => {
                console.error('KratorVoice Connection Error:', err);
                this.setStatus('Connection error', 'error');
            };

            this.ws.onclose = () => {
                this.stop();
            };

        } catch (err) {
            console.error('KratorVoice Start Error:', err);
            this.setStatus('Initialization Failed', 'error');
            throw err;
        }
    }

    stop() {
        this.isActive = false;
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(t => t.stop());
            this.audioStream = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        if (this.audioContext) {
            this.audioContext.close().catch(() => { });
            this.audioContext = null;
        }
        this.audioQueue = [];
        this.isPlayingQueue = false;
        this.isMicMuted = false;
        this.setStatus('Call ended', 'idle');
    }

    // --- STREAMING LOGIC ---
    startStreaming() {
        try {
            const source = this.audioContext.createMediaStreamSource(this.audioStream);
            const processor = this.audioContext.createScriptProcessor(4096, 1, 1);

            processor.onaudioprocess = (e) => {
                if (!this.isActive || !this.ws || this.ws.readyState !== WebSocket.OPEN || this.isMicMuted) return;

                const inputData = e.inputBuffer.getChannelData(0);
                const pcm16 = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    const s = Math.max(-1, Math.min(1, inputData[i]));
                    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }

                const base64Audio = btoa(String.fromCharCode(...new Uint8Array(pcm16.buffer)));
                this.ws.send(JSON.stringify({ type: 'input_audio_buffer.append', audio: base64Audio }));
            };

            source.connect(processor);
            processor.connect(this.audioContext.destination);
        } catch (error) {
            console.error('KratorVoice Streaming Error:', error);
        }
    }

    // --- PLAYBACK LOGIC ---
    async playAudioDelta(base64Audio) {
        try {
            const binaryString = atob(base64Audio);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) bytes[i] = binaryString.charCodeAt(i);

            const pcm16 = new Int16Array(bytes.buffer);
            const float32 = new Float32Array(pcm16.length);
            for (let i = 0; i < pcm16.length; i++) float32[i] = pcm16[i] / 32768;

            const audioBuffer = this.audioContext.createBuffer(1, float32.length, 24000);
            audioBuffer.getChannelData(0).set(float32);

            this.audioQueue.push(audioBuffer);
            if (!this.isPlayingQueue) this.playFromQueue();
        } catch (error) {
            console.error('KratorVoice Playback Error:', error);
        }
    }

    playFromQueue() {
        if (this.audioQueue.length === 0) {
            this.isPlayingQueue = false;
            return;
        }

        this.isPlayingQueue = true;
        this.setStatus('AI speaking...', 'speaking');

        const audioBuffer = this.audioQueue.shift();
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.audioContext.destination);

        const currentTime = this.audioContext.currentTime;
        const startTime = Math.max(currentTime, this.nextPlayTime);
        source.start(startTime);
        this.nextPlayTime = startTime + audioBuffer.duration;

        source.onended = () => {
            if (this.audioQueue.length > 0) {
                this.playFromQueue();
            } else {
                this.isPlayingQueue = false;
                if (this.isResponseDone) {
                    setTimeout(() => {
                        this.isMicMuted = false;
                        this.setStatus('Your turn', 'listening');
                    }, 300);
                }
            }
        };
    }

    // --- EVENT HANDLING ---
    async handleEvent(event) {
        switch (event.type) {
            case 'response.audio.delta':
                if (!this.isMicMuted) {
                    this.isMicMuted = true;
                    this.isResponseDone = false;
                }
                if (event.delta) await this.playAudioDelta(event.delta);
                break;

            case 'response.audio_transcript.done':
                if (event.transcript) this.onMessage('ai', event.transcript);
                break;

            case 'conversation.item.input_audio_transcription.completed':
                if (event.transcript) this.onMessage('user', event.transcript);
                break;

            case 'response.done':
                this.isResponseDone = true;
                break;

            case 'onboarding.complete':
                this.onComplete(event.final_summary);
                break;

            case 'onboarding.update':
                this.onUpdate(event);
                break;

            case 'error':
                this.setStatus('Server Error', 'error');
                break;
        }
    }

    setStatus(text, state) {
        this.onStatusChange(text, state);
    }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = KratorVoiceEngine;
} else {
    window.KratorVoiceEngine = KratorVoiceEngine;
}
