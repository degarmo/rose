// Door desk QR scanning. Frames are decoded on this device with the vendored
// jsQR library; nothing is sent anywhere until a code is found and searched.
(function () {
  var scanButton = document.getElementById('desk-scan');
  var panel = document.getElementById('desk-camera');
  var video = document.getElementById('desk-video');
  var statusLine = document.getElementById('desk-camera-status');
  var stopButton = document.getElementById('desk-camera-stop');
  var input = document.getElementById('desk-q');
  var CODE = /^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{3}-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{3}$/;
  var stream = null;
  var canvas = document.createElement('canvas');
  var context = canvas.getContext('2d', { willReadFrequently: true });

  if (!scanButton) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof jsQR !== 'function') {
    scanButton.hidden = true;
    return;
  }

  function stop() {
    if (stream) stream.getTracks().forEach(function (track) { track.stop(); });
    stream = null;
    panel.hidden = true;
  }

  function tick() {
    if (!stream) return;
    if (video.readyState === video.HAVE_ENOUGH_DATA) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      var frame = context.getImageData(0, 0, canvas.width, canvas.height);
      var found = jsQR(frame.data, frame.width, frame.height, { inversionAttempts: 'dontInvert' });
      if (found && CODE.test(found.data.trim())) {
        input.value = found.data.trim();
        stop();
        input.form.submit();
        return;
      }
    }
    requestAnimationFrame(tick);
  }

  scanButton.addEventListener('click', function () {
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment' }, audio: false })
      .then(function (media) {
        stream = media;
        video.srcObject = media;
        panel.hidden = false;
        statusLine.textContent = 'Point the camera at the member’s code.';
        return video.play();
      })
      .then(function () { requestAnimationFrame(tick); })
      .catch(function () {
        panel.hidden = false;
        statusLine.textContent = 'The camera is not available. Type the code instead.';
      });
  });
  stopButton.addEventListener('click', stop);
})();
