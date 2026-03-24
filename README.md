# SberDevices for Home Assistant

Интеграция умных устройств от SberDevices в Home Assistant.  
Написано очень плохо, для личных нужд, предоставлено как есть.

## Установка

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=altfoxie&repository=ha-sberdevices)

1. Установить менеджер дополнений [HACS](https://hacs.xyz/)
2. Зайти в меню **HACS** => **Integrations**
3. Ввести в поиск `SberDevices`, открыть
4. Установить интеграцию
5. Перезапустить Home Assistant

> [!NOTE]
> Конечно же, можно установить и вручную. В таком случае, нужно скопировать директорию `custom_components/` в корень конфигурации Home Assistant.

## Использование

1. В меню настроек Home Assistant выбрать **Devices & services**
2. Нажать кнопку в правом нижнем углу **Add integration**
3. Найти **SberDevices** и нажать на него
4. Перейти по ссылке авторизации и авторизоваться
5. Открыть консоль разработчика (F12) и скопировать URL неудачного перенаправления (`companionapp://...`).
   Google Chrome позволяет это сделать, нажав правой кнопкой мыши на ссылке и выбрав **Copy link address**.

   ![Ссылка](./images/redirect-url.jpg)

6. Вставьте скопированную ссылку в поле **URL** и нажмите **Submit**.
7. **Готово!** Ваши умные устройства должны появиться в списке устройств.
