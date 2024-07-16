@echo off
setlocal enabledelayedexpansion

:: Check if .env file exists
if not exist .env (
    echo .env file not found. Exiting.
    exit /b 1
)

:: Load .env file
for /f "usebackq tokens=*" %%a in (.env) do (
    set "line=%%a"
    :: Skip empty lines and comments
    if not "!line!"=="" if not "!line:~0,1!"=="#" (
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
echo AUTH0_CALLBACK_URL_CUSTOM=%AUTH0_CALLBACK_URL_CUSTOM%
echo STRIPE_SECRET_KEY=%STRIPE_SECRET_KEY%
echo STRIPE_PUBLISHABLE_KEY=%STRIPE_PUBLISHABLE_KEY%
echo STRIPE_WEBHOOK_SECRET=%STRIPE_WEBHOOK_SECRET%
echo BASIC_PLAN_PRICE_ID=%BASIC_PLAN_PRICE_ID%
echo PROFESSIONAL_PLAN_PRICE_ID=%PROFESSIONAL_PLAN_PRICE_ID%
echo ENTERPRISE_PLAN_PRICE_ID=%ENTERPRISE_PLAN_PRICE_ID%
echo DB_USERNAME=%DB_USERNAME%
echo DB_PASSWORD=%DB_PASSWORD%
echo DB_HOSTNAME=%DB_HOSTNAME%
echo DB_PORT=%DB_PORT%
echo DB_NAME=%DB_NAME%

:: Set environment variables on Heroku one by one
call :setHerokuConfig MAIL_SERVER %MAIL_SERVER%
call :setHerokuConfig MAIL_PORT %MAIL_PORT%
call :setHerokuConfig MAIL_USERNAME %MAIL_USERNAME%
call :setHerokuConfig MAIL_PASSWORD %MAIL_PASSWORD%
call :setHerokuConfig MAIL_DEFAULT_SENDER %MAIL_DEFAULT_SENDER%
call :setHerokuConfig AUTH0_CLIENT_ID %AUTH0_CLIENT_ID%
call :setHerokuConfig AUTH0_CLIENT_SECRET %AUTH0_CLIENT_SECRET%
call :setHerokuConfig AUTH0_DOMAIN %AUTH0_DOMAIN%
call :setHerokuConfig AUTH0_CALLBACK_URL_HEROKU %AUTH0_CALLBACK_URL_HEROKU%
call :setHerokuConfig AUTH0_CALLBACK_URL_CUSTOM %AUTH0_CALLBACK_URL_CUSTOM%
call :setHerokuConfig STRIPE_SECRET_KEY %STRIPE_SECRET_KEY%
call :setHerokuConfig STRIPE_PUBLISHABLE_KEY %STRIPE_PUBLISHABLE_KEY%
call :setHerokuConfig STRIPE_WEBHOOK_SECRET %STRIPE_WEBHOOK_SECRET%
call :setHerokuConfig BASIC_PLAN_PRICE_ID %BASIC_PLAN_PRICE_ID%
call :setHerokuConfig PROFESSIONAL_PLAN_PRICE_ID %PROFESSIONAL_PLAN_PRICE_ID%
call :setHerokuConfig ENTERPRISE_PLAN_PRICE_ID %ENTERPRISE_PLAN_PRICE_ID%
call :setHerokuConfig DB_USERNAME %DB_USERNAME%
call :setHerokuConfig DB_PASSWORD %DB_PASSWORD%
call :setHerokuConfig DB_HOSTNAME %DB_HOSTNAME%
call :setHerokuConfig DB_PORT %DB_PORT%
call :setHerokuConfig DB_NAME %DB_NAME%

echo Environment variables set successfully on Heroku.
exit /b 0

:setHerokuConfig
echo Setting %1 on Heroku
call heroku config:set %1=%2 -a raterware
exit /b 0
