import { Railway } from "@railwayapp/railway-sdk";

// TypeOwl - Infrastructure as Code
// Этот файл определяет оба сервиса: веб-апп и бот

export default {
  // Проект настройки
  project: "typeowl",

  // Сервисы
  services: {
    // 1. Веб-апп (фронтенд + API)
    web: {
      source: {
        type: "github",
        repo: "duskaimb2014/typeowl",  // замените на ваш GitHub username/repo
        branch: "main",
        rootDirectory: "/",
      },
      build: {
        builder: "nixpacks",
        buildCommand: "pip install -r requirements.txt",
      },
      deploy: {
        startCommand: "python web_server.py",
        healthcheckPath: "/",
        healthcheckTimeout: 300,
        restartPolicyType: "ON_FAILURE",
        restartPolicyMaxRetries: 10,
      },
      // Переменные окружения для веб-аппa
      variables: {
        PORT: "8080",
        PYTHONUNBUFFERED: "1",
      },
    },

    // 2. Telegram Бот
    bot: {
      source: {
        type: "github",
        repo: "duskaimb2014/typeowl",  // замените на ваш GitHub username/repo
        branch: "main",
        rootDirectory: "/",
      },
      build: {
        builder: "nixpacks",
        buildCommand: "pip install -r requirements.txt",
      },
      deploy: {
        startCommand: "python bot.py",
        restartPolicyType: "ON_FAILURE",
        restartPolicyMaxRetries: 10,
      },
      // Переменные окружения для бота
      variables: {
        TELEGRAM_BOT_TOKEN: "${{ secrets.TELEGRAM_BOT_TOKEN }}",
        WEB_APP_URL: "https://typeowl-production.up.railway.app",
        PYTHONUNBUFFERED: "1",
      },
    },
  },

  // Секреты (добавьте через Dashboard: Variables → Raw Editor)
  // TELEGRAM_BOT_TOKEN=9100945927:AAEXbPKVDn65CF2xA-3vygpX-AWdsESneZE
} satisfies Railway.Config;