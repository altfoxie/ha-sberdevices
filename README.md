# SberDevices for Home Assistant
Интеграция умных ламп (пока что?) от SberDevices в Home Assistant.  
Написано очень плохо, для личных нужд, предоставлено как есть.

## Установка
1. Установить менеджер дополнений [HACS](https://hacs.xyz/)
2. Зайти в меню **HACS** => **Integrations** => **3 точки** => **Custom repositories**
3. Заполнить небольшую форму значениями:  
    * **Repository**: `https://github.com/altfoxie/ha-sberdevices`  
    * **Category**: `Integration`
4. Перезапустить Home Assistant

> [!NOTE]
> Конечно же, можно установить и вручную. В таком случае, нужно скопировать директорию `custom_components/` в корень конфигурации Home Assistant.

## Использование
1. В меню настроек Home Assistant выбрать **Devices & services**
2. Нажать кнопку в правом нижнем углу **Add integration**
3. Найти **SberDevices** и нажать на него  
4. В браузере откроется окно авторизации Сбер ID.
    После авторизации, откройте консоль разработчика (F12) и найдите ошибку со ссылкой вида:  
    `companionapp://host?code=AA-XX-DD-LMAO-PYTHON-SUCKS&state=nevergonnagiveyouup`

    **Полностью скопируйте ссылку.** Google Chrome, например, позволяет это сделать, нажав правой кнопкой мыши на ссылке и выбрав **Copy link address**.

    ![Ссылка](./1.jpg)

4. Вернитесь в окно настройки интеграции. Если Вы получили ссылку быстрее чем за 10 секунд, можно заметить окно с заголовком `Wait 10 seconds`, немного подождите.
> Если кто знает, как корректно вызывать `configure` сразу после `external_step`, подскажите, пожалуйста.

5. Вставьте скопированную ссылку в поле **URL** и нажмите **Submit**.
6. **Готово!** Ваши умные лампы должны появиться в списке устройств.