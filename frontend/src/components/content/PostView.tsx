import { ArrowRight, CalendarHeart } from 'lucide-react'
import { Link } from 'react-router'
import type { JournalPost } from '@/lib/api'
import { formatEventDate, relativeDate } from '@/lib/format'
import { ButtonLink } from '../ui'
import { Carousel } from './Carousel'

interface PostViewProps {
  post: JournalPost
  headingLevel?: 'h1' | 'h2'
  showPermalink?: boolean
}

/** The same layout in the modal and on the permalink page. */
export function PostView({ post, headingLevel = 'h2', showPermalink = false }: PostViewProps) {
  const Heading = headingLevel
  return (
    <article className="grid gap-6 md:grid-cols-[1.25fr_1fr] md:gap-8">
      <Carousel images={post.images} label="Post images" />
      <div className="flex flex-col">
        <Heading className="sr-only">Journal post from {formatEventDate(post.published_at)}</Heading>
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-highlight">
          {post.author ?? 'The house'} &middot; <time dateTime={post.published_at}>{relativeDate(post.published_at)}</time>
        </p>
        <div
          className="mt-4 leading-relaxed text-fg-muted [&_a]:text-accent [&_a]:underline [&_a]:underline-offset-4"
          // Sanitised on the server: only <br> and https links survive.
          dangerouslySetInnerHTML={{ __html: post.caption_html }}
        />
        <div className="mt-8 flex flex-col gap-3 sm:flex-row md:mt-auto md:flex-col md:pt-8">
          {post.event && (
            <ButtonLink to={`/events/${post.event.slug}`} size="lg">
              <CalendarHeart aria-hidden="true" className="size-4" />
              RSVP
            </ButtonLink>
          )}
          {!post.event && post.cta && (
            <ButtonLink to={post.cta.url} size="lg">
              {post.cta.label}
            </ButtonLink>
          )}
          {showPermalink && (
            <Link
              to={`/journal/${post.slug}`}
              className="inline-flex min-h-11 items-center justify-center gap-2 text-sm text-fg-muted hover:text-fg"
            >
              Open as a page
              <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
          )}
        </div>
      </div>
    </article>
  )
}
