@echo off
setlocal enabledelayedexpansion

:: Load .env file
for /f "delims=" %%a in ('.env') do (
    set "line=%%a"
    if not "!line!"=="" (
        set "line=!line:#=!"
        for /f "tokens=1,* delims==" %%b in ("!line!") do set %%b=%%c
    )
)

:: Set environment variables on Heroku
heroku config:set MAIL_SERVER=%MAIL_SERVER% -a raterware
heroku config:set MAIL_PORT=%MAIL_PORT% -a raterware
heroku config:set MAIL_USERNAME=%MAIL_USERNAME% -a raterware
heroku config:set MAIL_PASSWORD=%MAIL_PASSWORD% -a raterware
heroku config:set MAIL_DEFAULT_SENDER=%MAIL_DEFAULT_SENDER% -a raterware
heroku config:set AUTH0_CLIENT_ID=%AUTH0_CLIENT_ID% -a raterware
heroku config:set AUTH0_CLIENT_SECRET=%AUTH0_CLIENT_SECRET% -a raterware
heroku config:set AUTH0_DOMAIN=%AUTH0_DOMAIN% -a raterware
heroku config:set AUTH0_CALLBACK_URL=%AUTH0_CALLBACK_URL% -a raterware
heroku config:set STRIPE_SECRET_KEY=%STRIPE_SECRET_KEY% -a raterware
heroku config:set STRIPE_PUBLISHABLE_KEY=%STRIPE_PUBLISHABLE_KEY% -a raterware

echo Environment variables set successfully on Heroku.
