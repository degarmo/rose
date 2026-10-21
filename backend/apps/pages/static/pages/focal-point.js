// Content > Page images: click (or use the arrow keys on) the picture to set the point that
// must always stay in view. It fills the two focal-point boxes, and the previews crop the
// picture the way the site will, through object-position.
;(function () {
  function ready(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn)
    else fn()
  }

  function clamp(value) {
    var number = parseFloat(value)
    return isFinite(number) ? Math.min(1, Math.max(0, number)) : 0.5
  }

  ready(function () {
    var root = document.querySelector('[data-focal]')
    var inputX = document.getElementById('id_focal_x')
    var inputY = document.getElementById('id_focal_y')
    if (!root || !inputX || !inputY) return
    var stage = root.querySelector('[data-focal-stage]')
    var image = root.querySelector('[data-focal-image]')
    var marker = root.querySelector('[data-focal-marker]')
    var crops = root.querySelector('[data-focal-crops]')
    var empty = root.querySelector('[data-focal-empty]')
    var previews = root.querySelectorAll('[data-focal-preview]')

    root.querySelectorAll('[data-ratio]').forEach(function (box) {
      box.style.aspectRatio = box.getAttribute('data-ratio').replace('/', ' / ')
    })

    function draw() {
      var x = clamp(inputX.value) * 100
      var y = clamp(inputY.value) * 100
      marker.style.left = x + '%'
      marker.style.top = y + '%'
      previews.forEach(function (preview) {
        preview.style.objectPosition = x + '% ' + y + '%'
      })
    }

    function set(x, y) {
      inputX.value = clamp(x).toFixed(2)
      inputY.value = clamp(y).toFixed(2)
      draw()
    }

    image.addEventListener('click', function (event) {
      var box = image.getBoundingClientRect()
      set((event.clientX - box.left) / box.width, (event.clientY - box.top) / box.height)
    })

    var steps = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }
    stage.addEventListener('keydown', function (event) {
      var step = steps[event.key]
      if (!step) return
      event.preventDefault()
      set(clamp(inputX.value) + step[0] * 0.05, clamp(inputY.value) + step[1] * 0.05)
    })

    inputX.addEventListener('input', draw)
    inputY.addEventListener('input', draw)

    // A newly chosen file previews straight away, before it is saved.
    var file = document.getElementById('id_image')
    if (file) {
      file.addEventListener('change', function () {
        var chosen = file.files && file.files[0]
        if (!chosen) return
        var url = URL.createObjectURL(chosen)
        image.src = url
        previews.forEach(function (preview) {
          preview.src = url
        })
        stage.hidden = false
        crops.hidden = false
        if (empty) empty.hidden = true
        set(0.5, 0.5)
      })
    }

    draw()
  })
})()
