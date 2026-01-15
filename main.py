from flask import Flask, render_template, request, flash, redirect, url_for, abort

from flask_login import LoginManager, login_user, login_required, current_user

from flask_login import logout_user 

from datetime import datetime



import pymysql

from dynaconf import Dynaconf

app = Flask(__name__)

config = Dynaconf(settings_file=["settings.toml"])

app.secret_key = config.secret_key

login_manager = LoginManager(app)

login_manager.login_view ='login'

class User:
    is_authenticated = True
    is_active = True
    is_anoymous = False


    def __init__(self, result):
        self.name = result['Name']
        self.email = result['Email']
        self.id = result['ID']

    def get_id(self):
        return str(self.id)
    
@login_manager.user_loader
def load_user(user_id):
    connection = connect_db()
    cursor = connection.cursor()


    cursor.execute("SELECT * FROM `User` WHERE `ID` = %s", (user_id) )

    result = cursor.fetchone()

    connection.close()

    if result is None:
        return None
    
    return User(result)
    


def connect_db():
    conn = pymysql.connect(
        host="db.steamcenter.tech",
        user="jquiles",
        password=config.password,
        database="jquiles_ricann_studios",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )

    return conn

@app.route("/")
def index():
    return render_template("homepage.html.jinja")

@app.route("/browse")
def browse():
    connection = connect_db()

    cursor = connection.cursor()

    cursor.execute('SELECT * FROM `Product`')

    result = cursor.fetchall()

    connection.close()

    return render_template("browse.html.jinja", products = result)


@app.route("/product/<product_id>")
def product_page(product_id):

    connection = connect_db()

    cursor = connection.cursor()

    cursor.execute('SELECT * FROM `Product` WHERE `ID` = %s', ( product_id ) )

    result = cursor.fetchone()
    
    cursor.execute("""
        SELECT 
            `Review` . `Rating`,
            `Review`. `Comments`,
            `User` . `Name` AS 'UserName'
        FROM `Review`
        JOIN `User` ON `Review`.`UserID` = `User`.`ID`
        WHERE `Review`.`ProductID` = %s
        """,
        (product_id,)
    )
    reviews = cursor.fetchall()


    connection.close()


    if result is None:
        abort(404)

    return render_template("product.html.jinja", product=result,  reviews=reviews)


@app.route("/product/<product_id>/add_review", methods=["POST"])
def add_review(product_id):
    user = request.form["user"]
    rating = request.form["rating"]
    comments = request.form["comment"]

    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO `Review` (`ProductID`, `UserID`, `Rating`, `Comments`)
        VALUES (%s, %s, %s, %s)
        """,
        (product_id, current_user.id, rating, comments)
    )

    connection.close()

    return redirect(f"/product/{product_id}")






@app.route("/product/<product_id>/add_to_cart", methods=["POST"])  
@login_required
def add_to_cart(product_id):

    quantity = request.form["qty"]
    
    connection = connect_db()

    cursor = connection.cursor()

    cursor.execute(" INSERT INTO `Cart` (`Quantity`,`ProductID`, `UserID` ) VALUES(%s, %s, %s) ON DUPLICATE KEY  UPDATE `Quantity` = `Quantity` + %s ", (quantity, product_id, current_user.id, quantity))

    connection.close()

    return redirect('/cart')



@app.route("/cart")
@login_required
def cart():
    connection = connect_db()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM  `Cart`
        JOIN `Product` ON `Product`.`ID` = `Cart`.`ProductID`
        WHERE `UserID` = %s
""", (current_user.id))
    
    results = cursor.fetchall()
    
    total = 0
    
    for x in results :
        total += float(x["Price"]) * int(x["Quantity"])

    connection.close()
    
    return render_template("cart.html.jinja", cart=results, total=total )


@app.route('/cart/<product_id>/update_qty', methods=["POST"])
@login_required
def update_crt(product_id):
    new_qty = request.form["qty"]

    connection = connect_db()
    cursor = connection.cursor()
    
    cursor.execute("""
        UPDATE `Cart` 
        SET `Quantity` = %s
        WHERE `ProductID`=%s AND `UserID`=%s                                  
""",(new_qty,product_id, current_user.id) )
    
    connection.close()
    return redirect('/cart')


@app.route('/cart/<item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    connection = connect_db()
    cursor = connection.cursor()
   
    cursor.execute("""
        DELETE FROM `Cart` WHERE `ProductID` = %s AND `UserID` = %s;
    """, (item_id, current_user.id))
    
    connection.close()
    return redirect('/cart')


@app.route("/checkout", methods = ["POST", "GET"])
@login_required
def checkout():
 
 connection = connect_db()
 
 
 cursor = connection.cursor()
 
 cursor.execute("""
        SELECT * FROM  `Cart`
        JOIN `Product` ON `Product`.`ID` = `Cart`.`ProductID`
        WHERE `UserID` = %s
""", (current_user.id))
 
 results = cursor.fetchall()
 
 if request.method == 'POST':

    cursor.execute("INSERT INTO `Sale` (`UserID`) VALUES (%s)",(current_user.id))

    sale = cursor.lastrowid
    for item in results:
        cursor.execute(""" 
        INSERT INTO `SaleCart` 
        (`ProductID`, `Quantity`, `SaleID`)
         VALUES (%s,%s,%s)
         """, (item['ProductID'], item['Quantity'], sale))
        
    
    cursor.execute("DELETE FROM `Cart` WHERE `UserID` = %s", (current_user.id))



    return redirect('/thanks')
 
 total = 0
 
 for x in results :
        total += float(x["Price"]) * int(x["Quantity"])
    
 connection.close()
    
 return render_template("checkout.html.jinja", cart=results, total=total )





@app.route("/thanks")
def thanks():
    return render_template("thanks.html.jinja")



@app.route("/orders")
@login_required
def orders():
    connection = connect_db()
    cursor = connection.cursor()


    cursor.execute("""
    SELECT 
        `Sale`.`ID`,
        `Sale`.`Timestamp`,
        `Sale`.`Status`,
        SUM(`SaleCart`.`Quantity`) AS 'Quantity',
        SUM(`SaleCart`.`Quantity` * `Product`.`Price`) AS 'Total'
    FROM `Sale`
    JOIN `SaleCart` ON `SaleCart`.`SaleID` = `Sale`.`ID`
    JOIN `Product` ON `Product`.`ID` = `SaleCart`.`ProductID`
    WHERE `Sale`.`UserID` = %s
    GROUP BY `Sale`.`ID`;
""", (current_user.id,))


    orders = cursor.fetchall()
    connection.close()

    return render_template("orders.html.jinja", orders=orders)









@app.route("/login",methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
         email = request.form["email"]
         
         password =request.form["password"]
         
         connection = connect_db()
         
         cursor = connection.cursor()

         cursor.execute('SELECT * FROM `User` WHERE `Email` = %s' , (email))

         result = cursor.fetchone()

         connection.close()

         if result is None:
             flash("No user found")
         elif password != result["Password"]:
             flash("Incorrect password")
         else:
             login_user(User(result))
             return redirect('/browse')
        

         
         
         
    return render_template("login.html.jinja")



@app.route("/register", methods=['POST', 'GET'])
def register():
    if request.method == 'POST':

        name = request.form["name"]

        email = request.form["email"]

        password =request.form["password"]

        confirm_password =request.form["confirm_password"]

        address = request.form["address"]

        if password != confirm_password:
            flash("Passwords do not match")
        elif len(password) < 8:
            flash("Password is too short")
        else:
            connection = connect_db()

            cursor = connection.cursor()
        

        try:
            cursor.execute("""
                    INSERT INTO `User` (`Name`, `Password`, `Email`, `Address`)
                    VALUES(%s, %s, %s, %s)
            """, (name, password, email, address))
            connection.close()
        except pymysql.err.IntegrityError:
            flash("Email already exits with an account")
            connection.close()
        else:
            return redirect('/login')
    

    return render_template("register.html.jinja")



@app.route("/logout", methods= ["POST", "GET"])
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html.jinja'), 404 


