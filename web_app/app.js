const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const hello = document.getElementById("hello");
const output = document.getElementById("output");
const btnStatus = document.getElementById("btn-status");
const btnSend = document.getElementById("btn-send");

const user = tg.initDataUnsafe?.user;

if (user) {
 hello.textContent = `Привет, ${user.first_name}!`;
} else {
 hello.textContent = "Привет! Данные пользователя недоступны.";
}

btnStatus.addEventListener("click", () => {
 if (user) {
 output.textContent =
 `Telegram ID: ${user.id}\n` +
 `Имя: ${user.first_name || ""}\n` +
 `Фамилия: ${user.last_name || ""}\n` +
 `Username: @${user.username || "нет"}`;
 } else {
 output.textContent = "Пользователь не найден.";
  }
});

btnSend.addEventListener("click", () => {
  const data = {
    action: "open_profile",
    user_id: user?.id || null
  };

  tg.sendData(JSON.stringify(data));
  output.textContent = "Данные отправлены боту.";
});