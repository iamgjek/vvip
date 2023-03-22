# 建立超級使用者
python manage.py createsuperuser

# 建立新的APP
python manage.py startapp ocr

# 資料表更新
python manage.py makemigrations
python manage.py migrate

# 查看遷移狀態
python manage.py showmigrations

# 重置資料庫(危險)
##(注意：使用此程式碼後，所有現有的超級使用者也將被刪除。)
##(只有表內資料清空)
python manage.py flush
---
### installation for Mac
Install Homebrew
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Install Homebrew Packages
```
$ brew install python@3.8
$ brew install libpython
$ brew install mysql
$ brew install gdal
```
Change Python version on Mac
```
$ ls -l /usr/local/bin/python*
$ ln -s -f /usr/local/bin/python3.8 /usr/local/bin/python
```

Tele-Marketing
No newline at end of file
Install Python Packages
```
$ bash install.mac.sh
```
### Run Server
```
$ . ../venv_vvip/bin/activate
$ python manage.py runserver 8000
```
No newline at end of file
