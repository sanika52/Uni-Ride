from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import Error
import bcrypt
import re
from functools import wraps
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-1234567890'

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sanu123',  # Your MySQL password
    'database': 'ride_sharing'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    # if 'user_id' in session:
    #     return redirect(url_for('dashboard'))
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('login'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                session['user_id'] = user['id']
                session['email'] = user['email']
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password.', 'error')
                
        except mysql.connector.Error as err:
            flash('Database error occurred.', 'error')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        roll_number = request.form.get('roll_number')
        college_name = request.form.get('college_name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Basic validation
        if not all([roll_number, college_name, email, password]):
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('register'))
            
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Invalid email format.', 'error')
            return redirect(url_for('register'))
            
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if email or roll number already exists
            cursor.execute('SELECT * FROM users WHERE email = %s OR roll_number = %s', (email, roll_number))
            if cursor.fetchone():
                flash('Email or roll number already exists.', 'error')
                return redirect(url_for('register'))
            
            # Hash password
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            # Insert new user
            cursor.execute(
                'INSERT INTO users (roll_number, college_name, email, password_hash) VALUES (%s, %s, %s, %s)',
                (roll_number, college_name, email, password_hash.decode('utf-8'))
            )
            conn.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except mysql.connector.Error as err:
            flash('Database error occurred.', 'error')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Database connection failed', 'error')
            return render_template('dashboard.html', rides=[], vehicles=[], requests=[])
            
        cursor = connection.cursor(dictionary=True)
        
        # Get user's rides
        cursor.execute('''
            SELECT r.*, u.email as driver_email, v.vehicle_model, v.vehicle_no
            FROM rides r
            JOIN users u ON r.driver_id = u.id
            JOIN vehicle v ON r.vehicle_id = v.vehicle_id
            WHERE r.driver_id = %s
            ORDER BY r.ride_date DESC, r.ride_time DESC
        ''', (session['user_id'],))
        rides = cursor.fetchall()
        
        # Get user's vehicles
        cursor.execute('SELECT * FROM vehicle WHERE user_id = %s', (session['user_id'],))
        vehicles = cursor.fetchall()

        # Get pending ride requests for the driver's rides
        cursor.execute('''
            SELECT rr.*, u.email as passenger_email, r.source_location, r.destination_location, 
                   r.ride_date, r.ride_time, v.vehicle_model, v.vehicle_no
            FROM Ride_Request rr
            JOIN rides r ON rr.matched_ride_id = r.ride_id
            JOIN users u ON rr.passenger_id = u.id
            JOIN vehicle v ON r.vehicle_id = v.vehicle_id
            WHERE r.driver_id = %s AND rr.status = 'pending'
            ORDER BY rr.created_at DESC
        ''', (session['user_id'],))
        requests = cursor.fetchall()
        
        return render_template('dashboard.html', rides=rides, vehicles=vehicles, requests=requests)
        
    except Exception as e:
        flash('Error fetching dashboard data: ' + str(e), 'error')
        return render_template('dashboard.html', rides=[], vehicles=[], requests=[])
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/create_ride', methods=['GET', 'POST'])
@login_required
def create_ride():
    if request.method == 'GET':
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Database connection failed', 'error')
                return render_template('create_ride.html', vehicles=[])
                
            cursor = connection.cursor(dictionary=True)
            
            # Get user's vehicles
            cursor.execute('SELECT * FROM vehicle WHERE user_id = %s', (session['user_id'],))
            vehicles = cursor.fetchall()
            
            return render_template('create_ride.html', vehicles=vehicles)
            
        except Exception as e:
            flash('Error fetching vehicles: ' + str(e), 'error')
            return render_template('create_ride.html', vehicles=[])
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
                
    elif request.method == 'POST':
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Database connection failed', 'error')
                return redirect(url_for('create_ride'))
                
            cursor = connection.cursor()
            
            source = request.form['source']
            destination = request.form['destination']
            ride_date = request.form['ride_date']   
            ride_time = request.form['ride_time']
            seats_offered = request.form['seats_offered']
            vehicle_id = request.form['vehicle_id']
            
            cursor.execute('''
                INSERT INTO rides (driver_id, vehicle_id, source_location, destination_location, 
                                 ride_date, ride_time, seats_offered)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (session['user_id'], vehicle_id, source, destination, ride_date, ride_time, seats_offered))
            
            connection.commit()
            flash('Ride created successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash('Error creating ride: ' + str(e), 'error')
            return redirect(url_for('create_ride'))
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

@app.route('/rides')
@login_required
def view_rides():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Database connection failed', 'error')
            return render_template('rides.html', rides=[])
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all available rides
        cursor.execute('''
            SELECT r.*, u.email as driver_email, v.vehicle_model, v.vehicle_no
            FROM rides r
            JOIN users u ON r.driver_id = u.id
            JOIN vehicle v ON r.vehicle_id = v.vehicle_id
            WHERE r.ride_date >= CURDATE()
            ORDER BY r.ride_date, r.ride_time
        ''')
        rides = cursor.fetchall()
        
        return render_template('rides.html', rides=rides)
        
    except Exception as e:
        flash('Error fetching rides: ' + str(e), 'error')
        return render_template('rides.html', rides=[])
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/join_ride', methods=['POST'])
@login_required
def join_ride():
    connection = None
    cursor = None
    try:
        data = request.get_json()
        ride_id = data.get('ride_id')
        
        if not ride_id:
            return jsonify({'error': 'Ride ID is required'}), 400
            
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get ride details for the request
        cursor.execute('''
            SELECT r.*, u.email as driver_email
            FROM rides r
            JOIN users u ON r.driver_id = u.id
            WHERE r.ride_id = %s
        ''', (ride_id,))
        ride = cursor.fetchone()
        
        if not ride:
            return jsonify({'error': 'Ride not found'}), 404
            
        # Check if user is the driver of this ride
        if ride['driver_id'] == session['user_id']:
            return jsonify({'error': 'You cannot request to join your own ride'}), 400
            
        # Check available seats
        cursor.execute('''
            SELECT r.seats_offered, COUNT(rp.participation_id) as current_passengers
            FROM rides r
            LEFT JOIN Ride_Participation rp ON r.ride_id = rp.ride_id AND rp.role = 'passenger'
            WHERE r.ride_id = %s
            GROUP BY r.ride_id
        ''', (ride_id,))
        seat_data = cursor.fetchone()
        
        if seat_data['current_passengers'] >= seat_data['seats_offered']:
            return jsonify({'error': 'No seats available'}), 400
            
        # Check if user already joined this ride
        cursor.execute('''
            SELECT * FROM Ride_Participation 
            WHERE ride_id = %s AND student_id = %s
        ''', (ride_id, session['user_id']))
        if cursor.fetchone():
            return jsonify({'error': 'You have already joined this ride'}), 400
            
        # Create ride request with all required fields
        cursor.execute('''
            INSERT INTO Ride_Request 
            (passenger_id, rider_source, rider_destination, preferred_date, preferred_time, 
             status, matched_ride_id) 
            VALUES (%s, %s, %s, %s, %s, 'pending', %s)
        ''', (session['user_id'], ride['source_location'], ride['destination_location'], 
              ride['ride_date'], ride['ride_time'], ride_id))
        
        connection.commit()
        return jsonify({'message': 'Join request sent successfully'})
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/handle_request', methods=['POST'])
@login_required
def handle_request():
    connection = None
    cursor = None
    try:
        if not request.is_json:
            return jsonify({'error': 'Invalid request format'}), 400
            
        data = request.get_json()
        request_id = data.get('request_id')
        ride_id = data.get('ride_id')
        action = data.get('action')
        
        if not all([request_id, ride_id, action]):
            return jsonify({'error': 'Missing required parameters'}), 400
            
        if action not in ['accept', 'reject']:
            return jsonify({'error': 'Invalid action'}), 400
            
        # Get database connection
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Verify that the ride belongs to the current user
        cursor.execute("SELECT driver_id FROM rides WHERE ride_id = %s", (ride_id,))
        ride = cursor.fetchone()
        
        if not ride or ride['driver_id'] != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        # Get the passenger_id from the request
        cursor.execute("SELECT passenger_id FROM Ride_Request WHERE request_id = %s", (request_id,))
        request_data = cursor.fetchone()
        if not request_data:
            return jsonify({'error': 'Request not found'}), 404
            
        passenger_id = request_data['passenger_id']
            
        # Update the request status
        new_status = 'matched' if action == 'accept' else 'rejected'
        cursor.execute("""
            UPDATE Ride_Request 
            SET status = %s 
            WHERE request_id = %s AND matched_ride_id = %s
        """, (new_status, request_id, ride_id))
        
        if cursor.rowcount == 0:
            connection.rollback()
            return jsonify({'error': 'Request not found or already processed'}), 404
            
        # If accepted, update the ride's available seats and add to Ride_Participation
        if action == 'accept':
            # Update available seats
            cursor.execute("""
                UPDATE rides r
                SET r.seats_offered = r.seats_offered - 1
                WHERE r.ride_id = %s
            """, (ride_id,))
            
            # Add to Ride_Participation
            cursor.execute("""
                INSERT INTO Ride_Participation (ride_id, student_id, role)
                VALUES (%s, %s, 'passenger')
            """, (ride_id, passenger_id))
            
            # Reject all other pending requests for this passenger and ride
            cursor.execute("""
                UPDATE Ride_Request
                SET status = 'rejected'
                WHERE passenger_id = %s AND matched_ride_id = %s AND request_id != %s AND status = 'pending'
            """, (passenger_id, ride_id, request_id))
            
        connection.commit()
        return jsonify({'message': f'Request {action}ed successfully'})
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/add_vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if request.method == 'GET':
        return render_template('add_vehicle.html')
        
    elif request.method == 'POST':
        connection = None
        cursor = None
        try:
            # Get form data
            vehicle_no = request.form.get('vehicle_no')
            vehicle_model = request.form.get('vehicle_model')
            seats_available = request.form.get('seats_available')
            
            # Validate form data
            if not all([vehicle_no, vehicle_model, seats_available]):
                flash('Please fill in all fields', 'error')
                return redirect(url_for('add_vehicle'))
                
            # Convert seats_available to integer
            try:
                seats_available = int(seats_available)
                if seats_available <= 0:
                    flash('Number of seats must be greater than 0', 'error')
                    return redirect(url_for('add_vehicle'))
            except ValueError:
                flash('Invalid number of seats', 'error')
                return redirect(url_for('add_vehicle'))
            
            # Get database connection
            connection = get_db_connection()
            if not connection:
                flash('Database connection failed', 'error')
                return redirect(url_for('add_vehicle'))
                
            cursor = connection.cursor()
            
            # Check if vehicle number already exists
            cursor.execute('SELECT vehicle_id FROM vehicle WHERE vehicle_no = %s', (vehicle_no,))
            if cursor.fetchone():
                flash('Vehicle with this number already exists', 'error')
                return redirect(url_for('add_vehicle'))
            
            # Insert new vehicle
            cursor.execute('''
                INSERT INTO vehicle (user_id, vehicle_no, vehicle_model, seats_available)
                VALUES (%s, %s, %s, %s)
            ''', (session['user_id'], vehicle_no, vehicle_model, seats_available))
            
            connection.commit()
            flash('Vehicle added successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except mysql.connector.Error as err:
            flash(f'Database error: {str(err)}', 'error')
            return redirect(url_for('add_vehicle'))
            
        except Exception as e:
            flash(f'Error adding vehicle: {str(e)}', 'error')
            return redirect(url_for('add_vehicle'))
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

@app.route('/profile')
@login_required
def profile():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Database connection failed', 'error')
            return redirect(url_for('dashboard'))
            
        cursor = connection.cursor(dictionary=True)
        
        # Get user details
        cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        
        # Get user's vehicles
        cursor.execute('SELECT * FROM vehicle WHERE user_id = %s', (session['user_id'],))
        vehicles = cursor.fetchall()
        
        # Get user's rides (as driver)
        cursor.execute('''
            SELECT r.*, COUNT(rp.participation_id) as passengers
            FROM rides r
            LEFT JOIN Ride_Participation rp ON r.ride_id = rp.ride_id AND rp.role = 'passenger'
            WHERE r.driver_id = %s
            GROUP BY r.ride_id
        ''', (session['user_id'],))
        driver_rides = cursor.fetchall()
        
        # Get user's rides (as passenger)
        cursor.execute('''
            SELECT r.*, u.email as driver_email
            FROM rides r
            JOIN Ride_Participation rp ON r.ride_id = rp.ride_id
            JOIN users u ON r.driver_id = u.id
            WHERE rp.student_id = %s AND rp.role = 'passenger'
        ''', (session['user_id'],))
        passenger_rides = cursor.fetchall()
        
        
        return render_template('profile.html', 
                             user=user, 
                             vehicles=vehicles, 
                             driver_rides=driver_rides, 
                             passenger_rides=passenger_rides)
                             
    except Exception as e:
        flash('Error fetching profile data: ' + str(e), 'error')
        return redirect(url_for('dashboard'))
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/search_rides', methods=['GET'])
@login_required
def search_rides():
    source = request.args.get('source', '')
    destination = request.args.get('destination', '')
    date = request.args.get('date', '')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = '''
            SELECT r.*, u.email as driver_email, v.vehicle_model, v.vehicle_no
            FROM rides r
            JOIN users u ON r.driver_id = u.id
            JOIN vehicle v ON r.vehicle_id = v.vehicle_id
            WHERE 1=1
        '''
        params = []
        
        if source:
            query += ' AND r.source_location LIKE %s'
            params.append(f'%{source}%')
        if destination:
            query += ' AND r.destination_location LIKE %s'
            params.append(f'%{destination}%')
        if date:
            query += ' AND r.ride_date = %s'
            params.append(date)
            
        query += ' ORDER BY r.ride_date, r.ride_time'
        
        cursor.execute(query, tuple(params))
        rides = cursor.fetchall()
        
    except mysql.connector.Error as err:
        flash('Error searching rides.', 'error')
        rides = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('rides.html', rides=rides)

@app.route('/get_pending_requests')
@login_required
def get_pending_requests():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all pending requests for rides where the current user is the driver
        cursor.execute('''
            SELECT rr.*, u.email as passenger_email
            FROM Ride_Request rr
            JOIN rides r ON rr.matched_ride_id = r.ride_id
            JOIN users u ON rr.passenger_id = u.id
            WHERE r.driver_id = %s
            AND rr.status = 'pending'
            ORDER BY rr.created_at DESC
        ''', (session['user_id'],))
        
        requests = cursor.fetchall()
        return jsonify({'requests': requests})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/delete_ride/<int:ride_id>', methods=['DELETE'])
@login_required
def delete_ride(ride_id):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Verify that the ride belongs to the current user
        cursor.execute("SELECT driver_id FROM rides WHERE ride_id = %s", (ride_id,))
        ride = cursor.fetchone()
        
        if not ride or ride['driver_id'] != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        # Delete in the correct order to maintain referential integrity
        
        # 1. Delete all ride requests for this ride
        cursor.execute("""
            DELETE FROM Ride_Request 
            WHERE matched_ride_id = %s
        """, (ride_id,))
        
        # 2. Delete all ride participations for this ride
        cursor.execute("""
            DELETE FROM Ride_Participation 
            WHERE ride_id = %s
        """, (ride_id,))
        
        # 3. Finally, delete the ride itself
        cursor.execute("""
            DELETE FROM rides 
            WHERE ride_id = %s AND driver_id = %s
        """, (ride_id, session['user_id']))
        
        if cursor.rowcount == 0:
            connection.rollback()
            return jsonify({'error': 'Ride not found or already deleted'}), 404
            
        connection.commit()
        return jsonify({'message': 'Ride deleted successfully'})
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8080) 