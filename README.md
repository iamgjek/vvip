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
