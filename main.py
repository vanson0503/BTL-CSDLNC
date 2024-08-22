import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from config import Config
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config.from_object(Config)

# Đảm bảo rằng thư mục upload được cấu hình
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Tạo thư mục nếu chưa tồn tại
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Kết nối tới MongoDB sử dụng MongoClient
client = MongoClient(app.config['MONGO_URI'])
db = client["libraryDB"]

@app.route('/')
def index():
    if 'user' in session:
        # Fetch counts from the database
        num_staff = db.staffs.count_documents({})
        num_users = db.users.count_documents({})
        num_books = db.books.count_documents({})
        num_available_books = db.books.count_documents({'availableCopies': {'$gt': 0}})

        # Render the index template with the fetched data
        return render_template('index.html', user=session['user'], num_staff=num_staff, num_users=num_users,
                               num_books=num_books, num_available_books=num_available_books)
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        collections = db.list_collection_names()

        user = db.staffs.find_one({'email': email, 'password': password})
        if user:
            session['user'] = user['name']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            error = "Invalid email or password. Please try again."
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


@app.route('/publishers', methods=['GET'])
def manage_publishers():
    if 'user' not in session:
        return redirect(url_for('login'))

    publishers = list(db.publishers.find())
    return render_template('manage_publishers.html', publishers=publishers)


@app.route('/publishers/add', methods=['POST'])
def add_publisher():
    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    address = request.form['address']
    phone = request.form['phone']
    email = request.form['email']
    db.publishers.insert_one({'name': name, 'address': address, 'phone': phone, 'email': email})

    return redirect(url_for('manage_publishers'))


@app.route('/publishers/edit/<id>', methods=['POST'])
def edit_publisher(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    address = request.form['address']
    phone = request.form['phone']
    email = request.form['email']
    db.publishers.update_one({'_id': ObjectId(id)},
                             {'$set': {'name': name, 'address': address, 'phone': phone, 'email': email}})
    return redirect(url_for('manage_publishers'))


@app.route('/publishers/delete/<id>', methods=['POST'])
def delete_publisher(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    db.publishers.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('manage_publishers'))


@app.route('/genres', methods=['GET'])
def manage_genres():
    if 'user' not in session:
        return redirect(url_for('login'))

    genres = list(db.genres.find())
    return render_template('manage_genres.html', genres=genres)


@app.route('/genres/add', methods=['POST'])
def add_genre():
    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    description = request.form['description']
    db.genres.insert_one({'name': name, 'description': description})

    return redirect(url_for('manage_genres'))


@app.route('/genres/edit/<id>', methods=['POST'])
def edit_genre(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    description = request.form['description']
    db.genres.update_one({'_id': ObjectId(id)}, {'$set': {'name': name, 'description': description}})
    return redirect(url_for('manage_genres'))


@app.route('/genres/delete/<id>', methods=['POST'])
def delete_genre(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    db.genres.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('manage_genres'))


@app.route('/books', methods=['GET'])
def manage_books():
    if 'user' not in session:
        return redirect(url_for('login'))

    books = list(db.books.find())
    genres = list(db.genres.find())
    publishers = list(db.publishers.find())

    genres_dict = {str(genre['_id']): genre['name'] for genre in genres}
    publishers_dict = {str(publisher['_id']): publisher['name'] for publisher in publishers}

    # Convert ObjectId to string for easier handling in JS
    for book in books:
        book['publisherId'] = str(book['publisherId'])
        book['genreIds'] = [str(genre_id) for genre_id in book['genreIds']]

    return render_template('manage_books.html', books=books, genres=genres, publishers=publishers,
                           genres_dict=genres_dict, publishers_dict=publishers_dict)


@app.route('/books/add', methods=['POST'])
def add_book():
    if 'user' not in session:
        return redirect(url_for('login'))

    title = request.form['title']
    author = request.form['author']
    isbn = request.form['isbn']
    published_year = int(request.form['publishedYear'])
    genre_ids = [ObjectId(id) for id in request.form.getlist('genres')]
    publisher_id = ObjectId(request.form['publisher'])
    summary = request.form['summary']
    total_copies = int(request.form['totalCopies'])
    available_copies = int(request.form['availableCopies'])

    cover_image = ''
    if 'coverImage' in request.files:
        file = request.files['coverImage']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            cover_image = filename

    db.books.insert_one({
        'title': title,
        'author': author,
        'ISBN': isbn,
        'publishedYear': published_year,
        'genreIds': genre_ids,
        'publisherId': publisher_id,
        'summary': summary,
        'coverImage': cover_image,
        'totalCopies': total_copies,
        'availableCopies': available_copies
    })

    return redirect(url_for('manage_books'))


@app.route('/books/edit/<id>', methods=['POST'])
def edit_book(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    title = request.form['title']
    author = request.form['author']
    isbn = request.form['isbn']
    published_year = int(request.form['publishedYear'])
    genre_ids = [ObjectId(id) for id in request.form.getlist('genres')]
    publisher_id = ObjectId(request.form['publisher'])
    summary = request.form['summary']
    total_copies = int(request.form['totalCopies'])
    available_copies = int(request.form['availableCopies'])

    # Xử lý upload ảnh bìa
    cover_image = None
    if 'coverImage' in request.files:
        file = request.files['coverImage']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cover_image = filename

    # Chuẩn bị dữ liệu cập nhật
    update_data = {
        'title': title,
        'author': author,
        'ISBN': isbn,
        'publishedYear': published_year,
        'genreIds': genre_ids,
        'publisherId': publisher_id,
        'summary': summary,
        'totalCopies': total_copies,
        'availableCopies': available_copies
    }

    # Nếu có ảnh bìa mới, cập nhật ảnh bìa
    if cover_image:
        update_data['coverImage'] = cover_image
    else:
        # Nếu không có ảnh mới, giữ lại ảnh bìa cũ
        book = db.books.find_one({'_id': ObjectId(id)})
        if book and 'coverImage' in book:
            update_data['coverImage'] = book['coverImage']

    # Cập nhật dữ liệu sách trong MongoDB
    db.books.update_one({'_id': ObjectId(id)}, {'$set': update_data})

    return redirect(url_for('manage_books'))


@app.route('/books/delete/<id>', methods=['POST'])
def delete_book(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    db.books.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('manage_books'))


@app.route('/users', methods=['GET'])
def manage_users():
    if 'user' not in session:
        return redirect(url_for('login'))

    users = list(db.users.find())
    return render_template('manage_users.html', users=users)


@app.route('/users/add', methods=['POST'])
def add_user():
    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    email = request.form['email']
    address = request.form['address']
    phone = request.form['phone']
    db.users.insert_one({'name': name, 'email': email, 'address': address, 'phone': phone})

    return redirect(url_for('manage_users'))


@app.route('/users/edit/<id>', methods=['POST'])
def edit_user(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    email = request.form['email']
    address = request.form['address']
    phone = request.form['phone']
    db.users.update_one({'_id': ObjectId(id)},
                        {'$set': {'name': name, 'email': email, 'address': address, 'phone': phone}})
    return redirect(url_for('manage_users'))


@app.route('/users/delete/<id>', methods=['POST'])
def delete_user(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    db.users.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('manage_users'))


@app.route('/staffs', methods=['GET'])
def manage_staffs():
    if 'user' not in session:
        return redirect(url_for('login'))

    staffs = list(db.staffs.find())
    return render_template('manage_staffs.html', staffs=staffs)


@app.route('/staffs/add', methods=['POST'])
def add_staff():
    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    db.staffs.insert_one({
        'name': name,
        'email': email,
        'password': password,
        'role': role,
        'shift': {
            'startTime': start_time,
            'endTime': end_time
        }
    })

    return redirect(url_for('manage_staffs'))


@app.route('/staffs/edit/<id>', methods=['POST'])
def edit_staff(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    email = request.form['email']
    role = request.form['role']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    db.staffs.update_one({'_id': ObjectId(id)}, {
        '$set': {
            'name': name,
            'email': email,
            'role': role,
            'shift': {
                'startTime': start_time,
                'endTime': end_time
            }
        }
    })
    return redirect(url_for('manage_staffs'))


@app.route('/staffs/delete/<id>', methods=['POST'])
def delete_staff(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    db.staffs.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('manage_staffs'))





@app.route('/borrowing', methods=['GET'])
def manage_borrowing_history():
    if 'user' not in session:
        return redirect(url_for('login'))

    borrowing_history = list(db.borrowing_history.find())
    users = list(db.users.find())
    books = list(db.books.find())
    staffs = list(db.staffs.find())

    # Chuyển ObjectId thành chuỗi và xây dựng từ điển
    users_dict = {str(user['_id']): user['name'] for user in users}
    books_dict = {str(book['_id']): book['title'] for book in books}
    staffs_dict = {str(staff['_id']): staff['name'] for staff in staffs}

    # Chuyển đổi ObjectId trong borrowing_history thành chuỗi
    for record in borrowing_history:
        record['userId'] = str(record['userId'])
        record['bookId'] = str(record['bookId'])
        record['staffId'] = str(record['staffId'])

    return render_template('manage_borrowing_history.html',
                           borrowing_history=borrowing_history,
                           users_dict=users_dict,
                           books_dict=books_dict,
                           staffs_dict=staffs_dict,
                           users=users,
                           books=books,
                           staffs=staffs)


@app.route('/borrowing/add', methods=['POST'])
def add_borrowing():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = ObjectId(request.form['user'])
    book_id = ObjectId(request.form['book'])
    borrowed_date = datetime.strptime(request.form['borrowedDate'], '%Y-%m-%dT%H:%M')
    due_date = datetime.strptime(request.form['dueDate'], '%Y-%m-%dT%H:%M')
    status = request.form['status']
    staff_id = ObjectId(request.form['staff'])

    # Kiểm tra số lượng bản copy
    book = db.books.find_one({'_id': book_id})
    if book['availableCopies'] <= 0:
        flash('No available copies for this book.')
        return redirect(url_for('manage_borrowing_history'))

    # Thêm bản ghi Borrowing History
    db.borrowing_history.insert_one({
        'userId': user_id,
        'bookId': book_id,
        'borrowedDate': borrowed_date,
        'dueDate': due_date,
        'status': status,
        'staffId': staff_id
    })

    # Giảm số lượng bản copy
    db.books.update_one({'_id': book_id}, {'$inc': {'availableCopies': -1}})

    return redirect(url_for('manage_borrowing_history'))


@app.route('/borrowing/edit/<id>', methods=['POST'])
def edit_borrowing(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = ObjectId(request.form['user'])
    book_id = ObjectId(request.form['book'])
    borrowed_date = datetime.strptime(request.form['borrowedDate'], '%Y-%m-%dT%H:%M')
    due_date = datetime.strptime(request.form['dueDate'], '%Y-%m-%dT%H:%M')
    return_date = None
    if request.form.get('returnDate'):
        return_date = datetime.strptime(request.form['returnDate'], '%Y-%m-%dT%H:%M')
    status = request.form['status']
    staff_id = ObjectId(request.form['staff'])

    # Lấy bản ghi hiện tại
    record = db.borrowing_history.find_one({'_id': ObjectId(id)})

    # Cập nhật số lượng bản copy khi thay đổi trạng thái
    if record['status'] != status:
        if status == 'returned' and record['status'] == 'borrowed':
            db.books.update_one({'_id': book_id}, {'$inc': {'availableCopies': 1}})
        elif status == 'borrowed' and record['status'] == 'returned':
            db.books.update_one({'_id': book_id}, {'$inc': {'availableCopies': -1}})

    # Cập nhật bản ghi Borrowing History
    db.borrowing_history.update_one(
        {'_id': ObjectId(id)},
        {'$set': {
            'userId': user_id,
            'bookId': book_id,
            'borrowedDate': borrowed_date,
            'dueDate': due_date,
            'returnDate': return_date,
            'status': status,
            'staffId': staff_id
        }}
    )

    return redirect(url_for('manage_borrowing_history'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
