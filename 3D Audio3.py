import webview
import numpy as np
import librosa
from sklearn.cluster import KMeans
import hashlib
import json

def generate_colors(audio_data):
    audio_hash = hashlib.md5(audio_data).hexdigest()
    np.random.seed(int(audio_hash[:8], 16))
    num_colors = 6
    random_colors = [np.random.randint(0, 256, 3) for _ in range(num_colors)]
    hex_colors = ['#' + ''.join(f'{c:02x}' for c in color) for color in random_colors]
    return hex_colors

def process_audio(file_path):
    audio, sample_rate = librosa.load(file_path, sr=16000)
    mel_spectrogram = librosa.feature.melspectrogram(y=audio, sr=sample_rate, n_mels=3, fmax=8000)
    mel_spectrogram_reshaped = mel_spectrogram.T
    
    num_clusters = 6
    kmeans = KMeans(n_clusters=num_clusters)
    kmeans.fit(mel_spectrogram_reshaped)
    
    with open(file_path, "rb") as f:
        audio_data = f.read()
    
    colors = generate_colors(audio_data)
    return colors

class API:
    def process_audio_file(self, file_path):
        colors = process_audio(file_path)
        return json.dumps(colors)

def load_html():
    html_content = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>3D Audio Visualizer</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <style>
            body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: Arial, sans-serif; }
            #upload-container { position: absolute; top: 20px; left: 20px; z-index: 10; }
            #file-upload { display: none; }
            #upload-label { background-color: #4CAF50; color: white; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
            #controls { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; background-color: rgba(0, 0, 0, 0.5); padding: 10px; border-radius: 5px; }
            #play-pause, #volume-control, #seek-bar { margin: 0 10px; }
            #instructions { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: white; font-size: 18px; pointer-events: none; }
            #error-message { position: absolute; top: 10px; right: 10px; background-color: #ff4444; color: white; padding: 10px; border-radius: 5px; display: none; }
        </style>
    </head>
    <body>
        <div id="upload-container">
            <label for="file-upload" id="upload-label">Upload Audio</label>
            <input type="file" id="file-upload" accept="audio/*">
        </div>

        <div id="controls">
            <button id="play-pause">Play</button>
            <input type="range" id="volume-control" min="0" max="1" step="0.1" value="1">
            <input type="range" id="seek-bar" min="0" max="100" value="0">
        </div>

        <div id="instructions">
            Upload an audio file to start the 3D visualization
        </div>

        <div id="error-message"></div>

        <script>
            let scene, camera, renderer, audioContext, analyser, dataArray, visualizer;
            let isPlaying = false;
            let audio = new Audio();
            let colors = [];
            let currentColorIndex = 0;

            function init() {
                scene = new THREE.Scene();
                camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
                renderer = new THREE.WebGLRenderer();
                renderer.setSize(window.innerWidth, window.innerHeight);
                document.body.appendChild(renderer.domElement);

                camera.position.z = 5;

                visualizer = new THREE.Group();
                scene.add(visualizer);

                // Create multiple spheres for a more complex visualization
                for (let i = 0; i < 10; i++) {
                    let sphere = new THREE.Mesh(
                        new THREE.SphereGeometry(0.2, 32, 32),
                        new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true })
                    );
                    sphere.position.set(
                        Math.random() * 4 - 2,
                        Math.random() * 4 - 2,
                        Math.random() * 4 - 2
                    );
                    visualizer.add(sphere);
                }

                window.addEventListener('resize', onWindowResize, false);

                animate();
            }

            function onWindowResize() {
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            }

            function animate() {
                requestAnimationFrame(animate);

                if (isPlaying && analyser) {
                    analyser.getByteFrequencyData(dataArray);
                    let average = dataArray.reduce((a, b) => a + b) / dataArray.length;
                    let scale = 1 + average / 128;
                    visualizer.scale.set(scale, scale, scale);

                    visualizer.rotation.x += 0.01;
                    visualizer.rotation.y += 0.01;

                    // Update colors based on audio intensity
                    if (colors.length > 0) {
                        currentColorIndex = Math.floor(average / (256 / colors.length));
                        visualizer.children.forEach((sphere, index) => {
                            sphere.material.color.setStyle(colors[(currentColorIndex + index) % colors.length]);
                        });
                    }

                    // Update individual sphere positions
                    visualizer.children.forEach((sphere, index) => {
                        let frequency = dataArray[index * 4] / 256;
                        sphere.position.y = (frequency - 0.5) * 2;
                    });
                }

                renderer.render(scene, camera);
            }

            document.getElementById('file-upload').addEventListener('change', function(e) {
                const file = e.target.files[0];
                const reader = new FileReader();

                reader.onload = function(e) {
                    audio.src = e.target.result;
                    audio.load();

                    // Process the audio file to get colors
                    pywebview.api.process_audio_file(file.path).then(result => {
                        colors = JSON.parse(result);
                        console.log('Generated colors:', colors);
                    }).catch(err => {
                        console.error('Error processing audio file:', err);
                        showError("Error processing audio file. Please try again.");
                    });

                    audio.addEventListener('canplaythrough', function() {
                        document.getElementById('instructions').style.display = 'none';
                        
                        audioContext = new (window.AudioContext || window.webkitAudioContext)();
                        analyser = audioContext.createAnalyser();
                        analyser.fftSize = 256;
                        dataArray = new Uint8Array(analyser.frequencyBinCount);

                        audioContext.resume().then(() => {
                            const source = audioContext.createMediaElementSource(audio);
                            source.connect(analyser);
                            analyser.connect(audioContext.destination);
                            console.log('Audio context resumed and connections made');
                        }).catch(err => {
                            console.error('Failed to resume audio context:', err);
                            showError("Failed to initialize audio. Please try again.");
                        });
                    });
                };

                reader.onerror = function(err) {
                    console.error('FileReader error:', err);
                    showError("Error reading the file. Please try again.");
                };

                reader.readAsDataURL(file);
            });

            document.getElementById('play-pause').addEventListener('click', function() {
                if (!audioContext) {
                    showError("Please upload an audio file first.");
                    return;
                }

                if (isPlaying) {
                    audio.pause();
                    this.textContent = 'Play';
                } else {
                    audio.play().then(() => {
                        console.log('Audio playback started');
                    }).catch(err => {
                        console.error('Failed to start audio playback:', err);
                        showError("Failed to play audio. Please try again.");
                    });
                    this.textContent = 'Pause';
                }
                isPlaying = !isPlaying;
            });

            document.getElementById('volume-control').addEventListener('input', function() {
                audio.volume = this.value;
            });

            document.getElementById('seek-bar').addEventListener('input', function() {
                const seekTime = audio.duration * (this.value / 100);
                audio.currentTime = seekTime;
            });

            audio.addEventListener('timeupdate', function() {
                const seekBar = document.getElementById('seek-bar');
                const value = (100 / audio.duration) * audio.currentTime;
                seekBar.value = value;
            });

            function showError(message) {
                const errorElement = document.getElementById('error-message');
                errorElement.textContent = message;
                errorElement.style.display = 'block';
                setTimeout(() => {
                    errorElement.style.display = 'none';
                }, 5000);
            }

            init();
        </script>
    </body>
    </html>
    '''

    api = API()
    window = webview.create_window('3D Audio Visualizer', html=html_content, js_api=api)
    webview.start()

if __name__ == '__main__':
    load_html()
