const BOT_PREFIX = process.env.BOT_PREFIX || '!';
const EMBED_COLOR = Number.parseInt(process.env.EMBED_COLOR || '0x0d0d0d', 16);
const THREAD_NAME = process.env.THREAD_NAME || '{match} ({gametype}) [{gameid}]';
const PING_ROLE_NAME = process.env.PING_ROLE_NAME || 'Leagues';
const SUPPORT_FOOTER = process.env.SUPPORT_FOOTER || 'Issues? Contact the host';

const TIER_ROLES = [
  'Overlord',
  'Dominator',
  'Alpha',
  'Phantom',
  'Skilled',
  'Rampage',
  'Improving',
  'Initiate',
  'Novice',
];

const GAME_TYPES = ['1s', '2s', '3s', '4s'];
const MATCH_TYPES = ['Default Loadout', 'Custom Loadout'];
const REGIONS = ['NA', 'EU', 'OCE', 'Asia', 'South America'];

module.exports = {
  BOT_PREFIX,
  EMBED_COLOR,
  THREAD_NAME,
  PING_ROLE_NAME,
  SUPPORT_FOOTER,
  TIER_ROLES,
  GAME_TYPES,
  MATCH_TYPES,
  REGIONS,
};
