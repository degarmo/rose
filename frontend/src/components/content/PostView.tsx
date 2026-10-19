import { Link } from 'react-router'
import type { JournalPost } from '@/lib/api'
import { cn } from '@/lib/cn'
import { formatEventDate, relativeDate } from '@/lib/format'
import { ButtonLink } from '../ui'
import { Carousel } from './Carousel'

interface PostViewProps {
  post: JournalPost
  headingLevel?: 'h1' | 'h2'
  showPermalink?: boolean
}

/**
 * One journal post, the same in the modal and on its own page: the pictures, then the
 * details between rules and the caption, as in the Event detail body.
 */
export function PostView({ post, headingLevel = 'h2', showPermalink = false }: PostViewProps) {
  const Heading = headingLevel
  return (
    <article className="grid gap-6 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)] md:gap-10">
      <Carousel images={post.images} label="Post images" />
      <div className="flex flex-col gap-5 lg:gap-6">
        <Heading className="sr-only">Journal post from {formatEventDate(post.published_at)}</Heading>
        <dl className={cn('grid grid-cols-2 gap-4 border-y border-border py-4 text-sm lg:py-6', post.event && 'lg:grid-cols-3')}>
          <div>
            <dt className="text-fg-muted">Posted</dt>
            <dd className="font-semibold text-fg">
              <time dateTime={post.published_at}>{relativeDate(post.published_at)}</time>
            </dd>
          </div>
          <div>
            <dt className="text-fg-muted">By</dt>
            <dd className="font-semibold text-fg">{post.author ?? 'The club'}</dd>
          </div>
          {post.event && (
            <div className="col-span-2 lg:col-span-1">
              <dt className="text-fg-muted">Event</dt>
              <dd className="font-semibold text-fg">{post.event.title}</dd>
            </div>
          )}
        </dl>
        <div
          className="text-fg lg:text-lead [&_a]:text-link [&_a]:underline [&_a]:underline-offset-4"
          // Sanitised on the server: only <br> and https links survive.
          dangerouslySetInnerHTML={{ __html: post.caption_html }}
        />
        {(post.event || post.cta || showPermalink) && (
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            {post.event && (
              <ButtonLink to={`/events/${post.event.slug}`} size="lg">
                RSVP
              </ButtonLink>
            )}
            {!post.event && post.cta && (
              <ButtonLink to={post.cta.url} size="lg">
                {post.cta.label}
              </ButtonLink>
            )}
            {showPermalink && (
              <Link to={`/journal/${post.slug}`} className="inline-flex min-h-6 items-center justify-center text-sm font-semibold text-link hover:text-primary-hover">
                Open as a page <span aria-hidden="true">&nbsp;→</span>
              </Link>
            )}
          </div>
        )}
      </div>
    </article>
  )
}
