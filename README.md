# Nexora

Локальное приложение для **включения и отключения интернета** на вашем ПК.

Открывается в браузере на `localhost` и управляет сетевыми адаптерами / NetworkManager.

## Возможности

- Один переключатель: интернет вкл / выкл
- Windows, Linux и macOS
- Статус адаптеров и подсказка, если не хватает прав администратора

## Установка

Нужен Python 3.10+.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Запуск

### Windows (самый простой способ)

1. Скачайте или клонируйте репозиторий.
2. Дважды щёлкните **`Nexora.bat`** (или `run-nexora.bat`).
3. Подтвердите запрос UAC (права администратора).
4. Откроется браузер с переключателем интернета.

Батник сам создаст `.venv`, поставит зависимости и запустит приложение.
Нужен установленный [Python 3.10+](https://www.python.org/downloads/) с галочкой **Add python.exe to PATH**.

### Через терминал

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m nexora
```

### Права администратора

Без повышенных прав переключение сети часто не сработает.

**Linux / macOS**:

```bash
sudo python -m nexora
```

Опции:

```bash
python -m nexora --no-browser
python -m nexora --port 8765
```


## Как это работает

| ОС | Способ |
| --- | --- |
| Windows | `Enable-NetAdapter` / `Disable-NetAdapter` для Ethernet и Wi‑Fi |
| Linux | `nmcli networking on/off` (или `ip link` как запасной вариант) |
| macOS | `networksetup -setnetworkserviceenabled` |

Сервер слушает только `127.0.0.1` — с других устройств в сети к нему не подключиться.

## Важно

- Это утилита **для вашего компьютера**, не удалённое управление чужим ПК.
- Отключение адаптеров обрывает текущие загрузки и онлайн-звонки.
- VPN и виртуальные адаптеры могут вести себя иначе, чем физические NIC.
