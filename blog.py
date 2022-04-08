from logging import log
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

# Kullanıcı Giriş Decorator'ı
def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return func(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapın!","danger")
            return redirect(url_for("login"))
    return decorated_function

# Kullanıcı Kayıt Formu.
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min = 4,max = 25)])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min = 5,max = 35)])
    email = StringField("Email Adresi",validators=[validators.Email("Geçerli Bir Email Adresi Giriniz")])
    password = PasswordField("Parola",validators=[
        validators.DataRequired("Lütfen Bir Parola Belirleyin"),
        validators.EqualTo(fieldname = "confirm",message = "Parolanız Uyuşmuyor")
    ])
    confirm = PasswordField("Parola Doğrula")

# Login Formu.
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

# Makale Formu.
class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.Length(min = 5,max = 100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min = 10)])

app = Flask(__name__)


# MySQL Konfigurasyonu.
app.config["MYSQL_HOST"] ="localhost"
app.config["MYSQL_USER"] ="root"
app.config["MYSQL_PASSWORD"] =""
app.config["MYSQL_DB"] ="blog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

# mysql objesini oluşturuyoruz.
mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/dashboard")
@login_required
def dashboard():

    cursor = mysql.connection.cursor()   # Cursor oluşturuyoruz.
    query = "Select * From articles where author = %s"
    result = cursor.execute(query,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")

# Kayıt İşlemleri
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():

        name = form.name.data   # Formdaki bilgileri veritabanına göndereceğimiz değerlerimize eşitliyoruz.
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        
        cursor = mysql.connection.cursor()   # Cursor Oluşturuyoruz.
        query = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"   # MySQL sorgumuzu yazdık.
        cursor.execute(query,(name,email,username,password))   # Sorguyu gönderdik.
        mysql.connection.commit()   # Sorguyu çalıştırdık.
        cursor.close()   # Cursorı kapatıyoruz.

        flash("Başarıyla kayıt oldunuz!","success")   # Flash mesajı patlatıyoruz.

        return redirect(url_for("login"))   # Eğer method POST ve form geçerli ise login sayfasına yönlendiriyoruz.

    else:
        return render_template("register.html",form = form)   # Eğer method GET ise register.html dosyasını renderlıyor ve form objesini gönderiyoruz.

# Login İşlemleri
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)   # request.form içindekiler LoginForm classımıza yerleşiyor ve bu classtan bir obje oluşturuyoruz.

    if request.method == "POST":

        username = form.username.data   # Formdaki bilgileri değerlerimize eşitliyoruz.
        password_entered = form.password.data

        cursor = mysql.connection.cursor()   # Cursor oluşturuyoruz.
        query = "Select * From users where username = %s"   # Öyle bir kullanıcı olup olmadığını sorguluyoruz.
        result = cursor.execute(query,(username,))   # Öyle bir kullanıcı yoksa 0 döndürür.

        if result > 0:

            data = cursor.fetchone()   # Veritabanından kullanıcının tüm bilgilerini sözlük olarak alıyoruz.
            real_password = data["password"]   # Kullanıcının veritabanındaki şifresini alıyoruz.

            if sha256_crypt.verify(password_entered,real_password):   # Girilen şifreyi kontrol ediyoruz.

                flash("Başarıyla giriş yapıldı!","success")   # Giriş yapıldı mesajını patlatıyoruz.

                session["logged_in"] = True   # Giriş yapıldığı için session logged_in anahtarımız true oluyor.
                session["username"] = username   # username anahtarına username'i eşitliyoruz.

                return redirect(url_for("index"))

            else:
                flash("Parolanızı yanlış girdiniz!","danger")
                return redirect(url_for("login"))

        else:
            flash("Böyle bir kullanıcı bulunmuyor!","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form = form)

# Logout İşlemleri
@app.route("/logout")
def logout():
    session.clear()   # Session'ı temizliyoruz
    return redirect(url_for("index"))

# Makale Ekleme
@app.route("/addarticle",methods = ["GET","POST"])
def add_article():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():

        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        query = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(query,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarıyla eklendi","success")

        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form = form)

# Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):

    cursor = mysql.connection.cursor()
    query = "Select * from articles where author = %s and id = %s"
    result = cursor.execute(query,(session["username"],id))   # Veritabanında o id ve authora denk makale yoksa 0 dönecektir.

    if result > 0:

        query2 = "Delete from articles where id = %s"
        cursor.execute(query2,(id,))
        mysql.connection.commit()

        return redirect(url_for("dashboard"))

    else:

        flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")

        return redirect(url_for("index"))

# Makale Güncelleme
@app.route("/edit/<string:id>",methods = ["GET","POST"])   # Formlarımız olacağı için GET POST methodlarını giriyoruz.
@login_required
def update(id):

    if request.method == "GET":
        
        cursor = mysql.connection.cursor()
        query = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(query,(id,session["username"]))

        if result == 0:

            flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
            return redirect(url_for("index"))

        else:

            article = cursor.fetchone()

            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]

            return render_template("update.html",form = form)

    else:   # POST request kısmı

        form = ArticleForm(request.form)
        new_title = form.title.data
        new_content = form.content.data

        query2 = "Update articles Set title = %s,content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(query2,(new_title,new_content,id))
        mysql.connection.commit()

        flash("Makale başarıyla güncellendi","success")

        return redirect(url_for("dashboard"))
        
# Makale Sayfası
@app.route("/articles")
def articles():

    cursor = mysql.connection.cursor()
    query = "Select * from articles"
    result = cursor.execute(query)   # Veritabanında makale yoksa 0 dönecektir.

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")

# Makale Detay Sayfası
@app.route("/article/<string:id>")
def article(id):

    cursor = mysql.connection.cursor()
    query = "Select * from articles where id = %s"
    result = cursor.execute(query,(id,))

    if result > 0:
        article = cursor.fetchone()    #   Veritabanından o id'deki article'ı alıyoruz.
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")

# Arama URL
@app.route("/search",methods = ["GET","POST"])
def search():

    if request.method == "GET":

       return redirect(url_for("index"))

    else:

        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()
        query = "Select * from articles where title like '%" + keyword + "%'"
        result = cursor.execute(query)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı","warning")
            return redirect(url_for("articles"))
        
        else:
            articles = cursor.fetchall()    # Search kısmına yazdığımız kelimeye uygun ne kadar makale başlığı varsa alıyoruz.
            return render_template("articles.html",articles = articles)

if __name__ == "__main__":
    app.run(debug = True)
