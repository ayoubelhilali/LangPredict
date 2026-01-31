// --- Configuration ---
const LANG_MAP = {
  "en-US": { label: "English", class: "en" },
  English: { label: "English", class: "en" },
  Anglais: { label: "English", class: "en" },
  "fr-FR": { label: "Français", class: "fr" },
  French: { label: "Français", class: "fr" },
  Français: { label: "Français", class: "fr" },
  "ar-MA": { label: "Darija", class: "da" },
  Darija: { label: "Darija", class: "da" },
  "Moroccan Darija": { label: "Darija", class: "da" },
};

// --- Elements ---
const textArea = document.getElementById("user_text");
const statusEl = document.getElementById("status-msg");
const resultContainer = document.getElementById("result-container");
const predictBtn = document.querySelector(".predict_btn");
const micBtn = document.getElementById("mic-btn");

// --- Helpers ---
function displayStatus(message, type = "success") {
  statusEl.style.display = "block";
  statusEl.innerHTML = message;
  if (type === "error") {
    statusEl.style.color = "#d32f2f";
    statusEl.style.backgroundColor = "#ffcdd2";
  } else {
    statusEl.style.color = "#1b5e20";
    statusEl.style.backgroundColor = "#e8f5e9";
  }
  setTimeout(() => {
    statusEl.style.display = "none";
  }, 5000);
}

function setBusyState(isBusy, text = "Identify Language") {
  predictBtn.disabled = isBusy;
  predictBtn.value = isBusy ? "Processing..." : text;

  if (isBusy) {
    resultContainer.innerHTML =
      '<div style="margin-top:20px; opacity:0.6;">Analyzing... <div class="loading-spinner"></div></div>';
  }
}

function updateResultUI(predictionKey, confidenceVal) {
  const langData = LANG_MAP[predictionKey] || {
    label: predictionKey || "Unknown",
    class: "da",
  };
  const confidenceDisplay =
    confidenceVal !== undefined && confidenceVal !== null
      ? `${confidenceVal}%`
      : "N/A";

  const html = `
          <div class="result-box ${langData.class}">
            <div class="result-header">
              <i class="fas fa-language"></i> ${langData.label}
            </div>
            <div class="result-score">Confidence Score: ${confidenceDisplay}</div>
          </div>
        `;
  resultContainer.innerHTML = html;
}

// --- Core Logic ---

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

function toggleRecording() {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
}

function startRecording() {
  navigator.mediaDevices.getUserMedia({ 
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      sampleRate: 16000
    } 
  })
    .then((stream) => {
      isRecording = true;
      audioChunks = [];
      
      // Try formats in order of preference for speech recognition
      const formats = [
        'audio/wav',
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4'
      ];
      
      let mimeType = '';
      for (const format of formats) {
        if (MediaRecorder.isTypeSupported(format)) {
          mimeType = format;
          console.log('✅ Using format:', format);
          break;
        }
      }
      
      if (!mimeType) {
        console.log('⚠️ No preferred format supported, using browser default');
      }
      
      const options = mimeType ? { 
        mimeType,
        audioBitsPerSecond: 128000
      } : {};
      
      mediaRecorder = new MediaRecorder(stream, options);
      console.log('🎙️ Recording with:', mediaRecorder.mimeType);
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          console.log('📦 Audio chunk received:', event.data.size, 'bytes');
          audioChunks.push(event.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
        console.log('🎵 Total audio size:', audioBlob.size, 'bytes, Type:', audioBlob.type);
        sendAudioToServer(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      // Request data every 100ms for better chunking
      mediaRecorder.start(100);
      micBtn.classList.add("mic-recording");
      textArea.placeholder = "🔴 Recording... Click mic to stop";
      displayStatus("Recording started. Speak clearly, then click mic to stop.", "success");
    })
    .catch((err) => {
      console.error("Microphone access denied:", err);
      displayStatus("Microphone access denied. Please allow microphone.", "error");
    });
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    isRecording = false;
    mediaRecorder.stop();
    micBtn.classList.remove("mic-recording");
    textArea.placeholder = "Processing audio...";
    setBusyState(true, "Analyzing...");
  }
}

function sendAudioToServer(audioBlob) {
  const formData = new FormData();
  
  // Determine file extension from mime type
  let extension = 'webm';
  if (audioBlob.type.includes('wav')) {
    extension = 'wav';
  } else if (audioBlob.type.includes('webm')) {
    extension = 'webm';
  } else if (audioBlob.type.includes('ogg')) {
    extension = 'ogg';
  } else if (audioBlob.type.includes('mp4') || audioBlob.type.includes('m4a')) {
    extension = 'mp4';
  }
  
  console.log('📤 Sending audio:', audioBlob.size, 'bytes as', extension);
  formData.append('audio_file', audioBlob, `recording.${extension}`);
  
  fetch("/upload", {
    method: "POST",
    body: formData,
  })
    .then((res) => res.json())
    .then((data) => {
      setBusyState(false);
      console.log('📥 Server response:', data);
      if (data.status === "success") {
        textArea.value = data.text || "";
        textArea.placeholder = "Type text here...";
        displayStatus("Audio processed successfully!");
        updateResultUI(data.prediction, data.confidence);
      } else {
        console.error('❌ Server error:', data.message, data.debug_info);
        displayStatus(data.message || "Processing failed", "error");
        textArea.placeholder = "Type text here...";
        resultContainer.innerHTML = "";
      }
    })
    .catch((err) => {
      console.error('❌ Network error:', err);
      setBusyState(false);
      resultContainer.innerHTML = "";
      textArea.placeholder = "Type text here...";
      displayStatus("Error processing audio.", "error");
    });
}

function uploadFile() {
  // // Create a temporary input
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = ".mp3, .wav";
  fileInput.onchange = () => {
    const file = fileInput.files[0];
    if (!file) return;
    setBusyState(true, "Uploading...");
    const formData = new FormData();
    formData.append("audio_file", file);
    fetch("/upload", {
      method: "POST",
      body: formData,
    })
      .then((res) => res.json())
      .then((data) => {
        setBusyState(false);
        if (data.status === "success") {
          textArea.value = data.text || "";
          displayStatus("File uploaded and processed!");
          updateResultUI(data.prediction, data.confidence);
        } else {
          displayStatus(data.message || "Upload failed", "error");
          resultContainer.innerHTML = "";
        }
      })
      .catch((err) => {
        console.error(err);
        setBusyState(false);
        resultContainer.innerHTML = "";
        displayStatus("Error uploading file.", "error");
      });
  };
  fileInput.click();
}
