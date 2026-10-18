import { CalendarCheck, EyeOff, FileText, Mail, ToggleLeft, Trash2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { PageHero } from '@/components/content/PageHero'
import { useSiteSettings } from '@/components/layout/siteSettingsContext'
import { Section } from '@/components/ui'
import { AGE_GATE_HOURS } from '@/lib/ageGate'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

function Block({ icon: Icon, title, children }: { icon: typeof EyeOff; title: string; children: ReactNode }) {
  return (
    <section className="border-t border-border pt-10">
      <h2 className="flex items-center gap-3 text-3xl text-fg">
        <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
        {title}
      </h2>
      <div className="mt-6 space-y-4 leading-relaxed text-fg-muted [&_li]:pl-1 [&_strong]:font-semibold [&_strong]:text-fg [&_ul]:list-disc [&_ul]:space-y-2 [&_ul]:pl-5">
        {children}
      </div>
    </section>
  )
}

export function PrivacyPage() {
  useDocumentMeta({
    title: 'Privacy',
    description: 'What we collect, what is never public, and how to ask us to delete your information.',
  })
  const settings = useSiteSettings()
  const email = settings.status === 'success' ? settings.data.contact_email : ''

  return (
    <>
      <PageHero
        eyebrow="Privacy"
        title="Your privacy is the point."
        lede="Discretion is the reason this community works. Here is exactly what we keep, in plain language."
        placeholder="shadow"
      />

      <Section width="narrow">
        <div className="space-y-14">
          <Block icon={FileText} title="What we collect">
            <ul>
              <li>
                <strong>When you contact us:</strong> the name you give, your email address, a phone number if you
                choose to add one, the topic, and your message. We use these only to reply to you.
              </li>
              <li>
                <strong>The age confirmation:</strong> a single cookie on your device that remembers you confirmed you
                are 18 or older. It expires after {AGE_GATE_HOURS} hours.
              </li>
              <li>
                <strong>If you create an account:</strong> your email address, the display name you choose and your
                password, which we store only in scrambled form. You can change your display name and password, or
                delete the account, at any time from your account page.
              </li>
              <li>
                <strong>When you RSVP:</strong> which evening, your party size and any note you leave for our hosts.
              </li>
              <li>
                <strong>Security cookies:</strong> a random token that stops other websites from sending forms in your
                name, and, while you are signed in, a session cookie. Neither contains anything about you.
              </li>
            </ul>
            <p>
              We do not store your IP address with your message. We do not use analytics, advertising pixels, social
              media widgets or any other third-party tracking, and our fonts are served from our own site.
            </p>
          </Block>

          <Block icon={EyeOff} title="What is never public">
            <p>
              Members are known on this site only by a display name they choose. Your legal name, email address and phone
              number are kept private and are never shown to the public or to other members.
            </p>
            <p>
              Photos and recordings are not allowed in the house. Any image you upload in future member features has its
              hidden location and camera data removed automatically, and is renamed so the original filename is not kept.
              We never show an image of an identifiable person unless that person has given their consent.
            </p>
            <p>
              When a message arrives, our team gets an email that says only that a message is waiting. What you wrote stays
              in our private system and is never copied into email.
            </p>
          </Block>

          <Block icon={CalendarCheck} title="Who can see your RSVPs">
            <p>
              Nobody but our hosts. Other guests, members and visitors never see who is coming, not even people
              going to the same evening. Some events show a total number of people attending, never names.
            </p>
            <p>
              Hosts see display names and party sizes on the door list so they can welcome you. Every download of
              that list is recorded with who downloaded it and when.
            </p>
            <p>
              We delete RSVPs 30 days after each event, keeping only how many people came. Calendar files you
              download just say &ldquo;Rose - Evening&rdquo; with no address unless you choose to include the details.
            </p>
          </Block>

          <Block icon={ToggleLeft} title="Social features are opt-in">
            <p>
              Member social features are <strong>off by default</strong>, and your profile starts out private. Nothing
              you do becomes visible to other members unless you turn it on.
            </p>
            <p>
              If you turn social features off later, everything you have posted is hidden from everyone straight away. It
              is not deleted, so it all comes back if you change your mind. If you would rather it be deleted, ask us and
              we will remove it.
            </p>
          </Block>

          <Block icon={Trash2} title="Asking us to delete your information">
            <p>
              You can delete your account yourself from your account page. That removes your profile and every RSVP
              straight away, and strips your name, email and phone number from any message you sent us. You can also
              ask us to delete anything else we hold about you, at any time. Send a request
              through the <Link to="/contact" className="text-accent underline underline-offset-4">contact form</Link>
              {email ? (
                <>
                  {' '}
                  or email{' '}
                  <a href={`mailto:${email}`} className="text-accent underline underline-offset-4">
                    {email}
                  </a>
                </>
              ) : null}
              , from the email address you used with us. We will confirm once it is done.
            </p>
          </Block>

          <Block icon={Mail} title="Email from us">
            <p>
              Any email we send comes from a plain sender name and uses a neutral subject line such as &ldquo;Your plans
              for Friday&rdquo;, so nothing in your inbox gives away who it is from or what it is about.
            </p>
          </Block>
        </div>
      </Section>
    </>
  )
}
