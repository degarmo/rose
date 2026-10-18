import { HandHeart, KeyRound, ShieldCheck, UsersRound, type LucideIcon } from 'lucide-react'

export interface Value {
  title: string
  short: string
  long: string
  icon: LucideIcon
}

export const VALUES: Value[] = [
  {
    title: 'Consent',
    short: 'Asked for, freely given, and always revocable.',
    long: 'Every interaction here begins with a clear yes and can end with a simple no. We teach consent as a skill, practise it openly and expect it from everyone who walks through the door.',
    icon: KeyRound,
  },
  {
    title: 'Inclusion',
    short: 'Every body, identity and level of experience.',
    long: 'People of every gender, orientation, background, shape and ability belong here. Curiosity is the only prerequisite, and nobody is ever made to feel new for being new.',
    icon: UsersRound,
  },
  {
    title: 'Safety',
    short: 'Trained hosts, clear agreements, real follow-through.',
    long: 'Volunteer hosts are on the floor at every gathering, our community agreements are short and specific, and every concern raised with us is taken seriously and handled privately.',
    icon: ShieldCheck,
  },
  {
    title: 'Community',
    short: 'Run by members, for members, at a human scale.',
    long: 'We are a nonprofit kept alive by volunteers who teach, host, clean up and look out for one another. The house is what we build together, one evening at a time.',
    icon: HandHeart,
  },
]
