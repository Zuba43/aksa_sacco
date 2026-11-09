from app import create_app, db
from app.models import User

app = create_app()

def seed_database():
    with app.app_context():
        # Clear existing users or check if they exist
        print("-> Checking and seeding demo user accounts...")

        demo_users = [
            {
                "fname": "Edinah",
                "lname": "Niwenyesiga",
                "username": "edinah_sec",
                "phone": "0787455260",
                "email": "edinah@aksa.com",
                "password": "edinah123!",
                "role": "secretary",
                "home_district": "Ibanda",
                "nin": "CF1234567890AB",
                "gender": "Female",
                "dob": "1995-05-12",
                # Emergency Contact 1
                "emergency_name_1": "Alice Tumwine",
                "emergency_phone_1": "0771000001",
                "emergency_relation_1": "Mother",
                # Emergency Contact 2
                "emergency_name_2": "Robert Niwenyesiga",
                "emergency_phone_2": "0771000002",
                "emergency_relation_2": "Father",
                # Contact 3: Next of Kin
                "nok_name": "John Bosco",
                "nok_phone": "0771122334",
                "nok_relation": "Brother"
            },
            {
                "fname": "John",
                "lname": "Kakama",
                "username": "kakama_tres",
                "phone": "0700415776",
                "email": "kakama@aksa.com",
                "password": "KakaJ!",
                "role": "treasurer",
                "home_district": "Mbarara",
                "nin": "CF9876543210XY",
                "gender": "Male",
                "dob": "1990-10-20",
                # Emergency Contact 1
                "emergency_name_1": "Ester Kakama",
                "emergency_phone_1": "0702000001",
                "emergency_relation_1": "Mother",
                # Emergency Contact 2
                "emergency_name_2": "James Kakama",
                "emergency_phone_2": "0702000002",
                "emergency_relation_2": "Sibling",
                # Contact 3: Next of Kin
                "nok_name": "Mary Kakama",
                "nok_phone": "0702233445",
                "nok_relation": "Spouse"
            },
            {
                "fname": "Arthur",
                "lname": "Chair",
                "username": "chair_main",
                "phone": "0770000001",
                "email": "chair@aksa.com",
                "password": "chair123!",
                "role": "chair",
                "home_district": "Kampala",
                "nin": "CM1111222233AA",
                "gender": "Male",
                "dob": "1985-02-15",
                # Emergency Contact 1
                "emergency_name_1": "Grace Chair",
                "emergency_phone_1": "0779000001",
                "emergency_relation_1": "Mother",
                # Emergency Contact 2
                "emergency_name_2": "Peter Chair",
                "emergency_phone_2": "0779000002",
                "emergency_relation_2": "Father",
                # Contact 3: Next of Kin
                "nok_name": "Sarah Chair",
                "nok_phone": "0779988776",
                "nok_relation": "Spouse"
            },
            {
                "fname": "Finance",
                "lname": "Officer",
                "username": "finance_dept",
                "phone": "0770000002",
                "email": "finance@aksa.com",
                "password": "finance123!",
                "role": "finance",
                "home_district": "Entebbe",
                "nin": "CF4444555566BB",
                "gender": "Female",
                "dob": "1992-08-04",
                # Emergency Contact 1
                "emergency_name_1": "Martha Officer",
                "emergency_phone_1": "0775000001",
                "emergency_relation_1": "Mother",
                # Emergency Contact 2
                "emergency_name_2": "Paul Officer",
                "emergency_phone_2": "0775000002",
                "emergency_relation_2": "Guardian/Friend",
                # Contact 3: Next of Kin
                "nok_name": "David Officer",
                "nok_phone": "0775544332",
                "nok_relation": "Parent"
            },
            {
                "fname": "Regular",
                "lname": "Member",
                "username": "member_one",
                "phone": "0770000003",
                "email": "member@aksa.com",
                "password": "member123!",
                "role": "member",
                "home_district": "Ibanda",
                "nin": "CM7777888899CC",
                "gender": "Male",
                "dob": "1998-12-01",
                # Emergency Contact 1
                "emergency_name_1": "Agnes Member",
                "emergency_phone_1": "0773000001",
                "emergency_relation_1": "Mother",
                # Emergency Contact 2
                "emergency_name_2": "Mark Member",
                "emergency_phone_2": "0773000002",
                "emergency_relation_2": "Father",
                # Contact 3: Next of Kin
                "nok_name": "Grace Member",
                "nok_phone": "0773322110",
                "nok_relation": "Sibling"
            }
        ]

        for u_data in demo_users:
            existing_user = User.query.filter((User.username == u_data["username"]) | (User.phone == u_data["phone"])).first()
            if not existing_user:
                user = User(
                    fname=u_data["fname"],
                    lname=u_data["lname"],
                    username=u_data["username"],
                    phone=u_data["phone"],
                    email=u_data["email"],
                    role=u_data["role"],
                    home_district=u_data["home_district"],
                    nin=u_data["nin"],
                    gender=u_data["gender"],
                    dob=u_data["dob"],
                    # 3 Contacts mapping
                    emergency_name_1=u_data["emergency_name_1"],
                    emergency_phone_1=u_data["emergency_phone_1"],
                    emergency_relation_1=u_data["emergency_relation_1"],
                    emergency_name_2=u_data["emergency_name_2"],
                    emergency_phone_2=u_data["emergency_phone_2"],
                    emergency_relation_2=u_data["emergency_relation_2"],
                    nok_name=u_data["nok_name"],
                    nok_phone=u_data["nok_phone"],
                    nok_relation=u_data["nok_relation"],
                    is_active_account=True # Pre-activated for immediate testing
                )
                user.set_password(u_data["password"])
                db.session.add(user)
                print(f" -> Created demo user: {u_data['fname']} {u_data['lname']} ({u_data['role']})")
            else:
                print(f" -> User {u_data['username']} already exists. Skipping.")

        db.session.commit()
        print("-> Database seeding complete!")

if __name__ == '__main__':
    seed_database()