const { Client, GatewayIntentBits, Events } = require('discord.js');
const { BOT_PREFIX, EMBED_COLOR } = require('./config');
require('dotenv').config();

if (!process.env.DISCORD_TOKEN) {
  console.error('Missing DISCORD_TOKEN. Add it to your .env file.');
  process.exit(1);
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

client.once(Events.ClientReady, (readyClient) => {
  console.log(`✅ Logged in as ${readyClient.user.tag}`);
  readyClient.user.setPresence({
    activities: [{ name: 'your server' }],
    status: 'online',
  });
});

client.on(Events.MessageCreate, async (message) => {
  if (message.author.bot) return;

  const content = message.content.toLowerCase();

  if (content === `${BOT_PREFIX}ping`) {
    await message.reply('Pong! 🏓');
  } else if (content === `${BOT_PREFIX}hello`) {
    await message.reply(`Hello, ${message.author.username}!`);
  } else if (content === `${BOT_PREFIX}help`) {
    await message.reply(`Commands: ${BOT_PREFIX}ping, ${BOT_PREFIX}hello, ${BOT_PREFIX}help`);
  }
});

client.on(Events.Error, (error) => {
  console.error('Discord client error:', error);
});

client.login(process.env.DISCORD_TOKEN);
