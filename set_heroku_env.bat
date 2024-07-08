@echo off
setlocal enabledelayedexpansion

:: Load .env file
for /f "usebackq tokens=*" %%a in (.env) do (
    set "line=%%a"
    if defined line (
        set "line=!line:#=!"
        for /f "tokens=1,* delims==" %%b in ("!line!") do set %%b=%%c
    )
)

:: Debug statements to verify variable values
echo MAIL_SERVER=%MAIL_SERVER%
echo MAIL_PORT=%MAIL_PORT%
echo MAIL_USERNAME=%MAIL_USERNAME%
echo MAIL_PASSWORD=%MAIL_PASSWORD%
echo MAIL_DEFAULT_SENDER=%MAIL_DEFAULT_SENDER%
echo AUTH0_CLIENT_ID=%AUTH0_CLIENT_ID%
echo AUTH0_CLIENT_SECRET=%AUTH0_CLIENT_SECRET%
echo AUTH0_DOMAIN=%AUTH0_DOMAIN%
echo AUTH0_CALLBACK_URL_HEROKU=%AUTH0_CALLBACK_URL_HEROKU%
::echo AUTH0_CALLBACK_URL_CUSTOM=%AUTH0_CALLBACK_URL_CUSTOM%
echo STRIPE_SECRET_KEY=%STRIPE_SECRET_KEY%
echo STRIPE_PUBLISHABLE_KEY=%STRIPE_PUBLISHABLE_KEY%

:: Set environment variables on Heroku one by one
echo Setting MAIL_SERVER on Heroku
call heroku config:set MAIL_SERVER=%MAIL_SERVER% -a raterware

echo Setting MAIL_PORT on Heroku
call heroku config:set MAIL_PORT=%MAIL_PORT% -a raterware

echo Setting MAIL_USERNAME on Heroku
call heroku config:set MAIL_USERNAME=%MAIL_USERNAME% -a raterware

echo Setting MAIL_PASSWORD on Heroku
call heroku config:set MAIL_PASSWORD=%MAIL_PASSWORD% -a raterware

echo Setting MAIL_DEFAULT_SENDER on Heroku
call heroku config:set MAIL_DEFAULT_SENDER=%MAIL_DEFAULT_SENDER% -a raterware

echo Setting AUTH0_CLIENT_ID on Heroku
call heroku config:set AUTH0_CLIENT_ID=%AUTH0_CLIENT_ID% -a raterware

echo Setting AUTH0_CLIENT_SECRET on Heroku
call heroku config:set AUTH0_CLIENT_SECRET=%AUTH0_CLIENT_SECRET% -a raterware

echo Setting AUTH0_DOMAIN on Heroku
call heroku config:set AUTH0_DOMAIN=%AUTH0_DOMAIN% -a raterware

echo Setting AUTH0_CALLBACK_URL_HEROKU on Heroku
call heroku config:set AUTH0_CALLBACK_URL_HEROKU=%AUTH0_CALLBACK_URL_HEROKU% -a raterware

echo Setting AUTH0_CALLBACK_URL_CUSTOM on Heroku
call heroku config:set AUTH0_CALLBACK_URL_CUSTOM=%AUTH0_CALLBACK_URL_CUSTOM% -a raterware

echo Setting STRIPE_SECRET_KEY on Heroku
call heroku config:set STRIPE_SECRET_KEY=%STRIPE_SECRET_KEY% -a raterware

echo Setting STRIPE_PUBLISHABLE_KEY on Heroku
call heroku config:set STRIPE_PUBLISHABLE_KEY=%STRIPE_PUBLISHABLE_KEY% -a raterware

echo Environment variables set successfully on Heroku.
