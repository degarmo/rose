/**
 * Renders guidelines written as plain text: blank lines split sections, the
 * first line of a section followed by "- " bullets becomes a heading.
 */
export function GuidelinesText({ body }: { body: string }) {
  const sections = body.split(/\n\s*\n/).map((block) => block.split('\n').map((line) => line.trim()).filter(Boolean))
  return (
    <div className="space-y-5 leading-relaxed text-fg-muted">
      {sections.map((lines, index) => {
        const bullets = lines.filter((line) => line.startsWith('- '))
        const text = lines.filter((line) => !line.startsWith('- '))
        if (bullets.length === 0) {
          return <p key={index}>{text.join(' ')}</p>
        }
        return (
          <section key={index}>
            {text.length > 0 && <h3 className="mb-2 font-display text-xl text-fg">{text.join(' ')}</h3>}
            <ul className="list-disc space-y-1.5 pl-5">
              {bullets.map((line) => (
                <li key={line}>{line.slice(2)}</li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
