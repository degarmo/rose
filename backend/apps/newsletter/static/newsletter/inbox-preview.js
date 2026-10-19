// Live inbox preview on the newsletter form: mirrors the subject and preheader
// fields as they are typed, the way an inbox list would show them.
document.addEventListener('DOMContentLoaded', () => {
  const preview = document.querySelector('[data-inbox-preview]')
  const subject = document.getElementById('id_subject')
  const preheader = document.getElementById('id_preheader')
  if (!preview || !subject) return
  const subjectOut = preview.querySelector('[data-preview-subject]')
  const preheaderOut = preview.querySelector('[data-preview-preheader]')
  const update = () => {
    subjectOut.textContent = subject.value.trim() || '(no subject yet)'
    const extra = preheader ? preheader.value.trim() : ''
    preheaderOut.textContent = extra ? ` - ${extra}` : ''
  }
  subject.addEventListener('input', update)
  if (preheader) preheader.addEventListener('input', update)
  update()
})
