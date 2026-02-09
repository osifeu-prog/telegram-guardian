
bot.onText(/\/app/, (msg) => {
  const chatId = msg.chat.id;

  bot.sendMessage(chatId, "???? ?? ?????????…", {
    reply_markup: {
      keyboard: [
        [
          {
            text: "??? ????????",
            web_app: { url: "https://slhwallet-production.up.railway.app/webapp/index.html" }
          }
        ]
      ],
      resize_keyboard: true,
      one_time_keyboard: true
    }
  });
});

bot.onText(/\/app/, (msg) => {
  const chatId = msg.chat.id;

  bot.sendMessage(chatId, "???? ?? ?????????…", {
    reply_markup: {
      keyboard: [
        [
          {
            text: "??? ????????",
            web_app: { url: "https://slhwallet-production.up.railway.app/webapp/index.html" }
          }
        ]
      ],
      resize_keyboard: true,
      one_time_keyboard: true
    }
  });
});
