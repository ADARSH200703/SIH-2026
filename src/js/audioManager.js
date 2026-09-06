/**
 * Avionics Sound Synthesizer — Web Audio API
 * Engine hum, warning beeps, and alert klaxon.
 */
export class AudioManager {
  constructor() {
    this._ctx      = null;
    this._gain     = null;
    this._osc      = null;
    this.isMuted   = true;
    this._ready    = false;
  }

  _init() {
    if (this._ready) return;
    this._ctx  = new (window.AudioContext || window.webkitAudioContext)();
    this._osc  = this._ctx.createOscillator();
    this._gain = this._ctx.createGain();
    const lpf  = this._ctx.createBiquadFilter();
    lpf.type = 'lowpass';
    lpf.frequency.value = 140;

    this._osc.type = 'sawtooth';
    this._osc.frequency.value = 65;
    this._gain.gain.value = 0;

    this._osc.connect(lpf).connect(this._gain).connect(this._ctx.destination);
    this._osc.start();
    this._ready = true;
  }

  toggleMute() {
    this._init();
    if (this._ctx.state === 'suspended') this._ctx.resume();
    this.isMuted = !this.isMuted;
    this._gain.gain.setValueAtTime(this.isMuted ? 0 : 0.04, this._ctx.currentTime);
    return !this.isMuted;
  }

  updateEngineRPM(rpm) {
    if (!this._ready || this.isMuted) return;
    this._osc.frequency.setTargetAtTime(40 + (rpm / 4500) * 45, this._ctx.currentTime, 0.1);
  }

  _tone(freq, duration, type = 'sine', volume = 0.1) {
    if (!this._ready || this.isMuted) return;
    const osc  = this._ctx.createOscillator();
    const gain = this._ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(volume, this._ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this._ctx.currentTime + duration);
    osc.connect(gain).connect(this._ctx.destination);
    osc.start();
    osc.stop(this._ctx.currentTime + duration);
  }

  playWarning()  { this._tone(720, 0.18, 'triangle'); setTimeout(() => this._tone(880, 0.22, 'triangle'), 150); }
  playCritical() { this._tone(980, 0.15, 'square');   setTimeout(() => this._tone(620, 0.25, 'square'),   120); }
  playSuccess()  {
    [523.25, 659.25, 783.99].forEach((f, i) => setTimeout(() => this._tone(f, 0.15), i * 100));
  }
}
