create database healthcareAnalyticsSystem;
create table patient(
patient_id varchar (50) primary key,
first_name varchar (50) ,
last_name varchar (50) ,
gender varchar (50),
address varchar (50));
select * from patient;
create table hospital(
hospital_id  varchar (50) primary key ,
contact_number BIGINT (100),
hospital_address varchar(50),
hospital_name varchar(50)
); 
select * from hospital;
create table doctor(
doctor_id varchar(50) primary key ,
hospital_id varchar(50),
name  varchar(50),
contact_number bigint,
speacilization varchar(50),
foreign key (hospital_id) references hospital(hospital_id)
);
select* from doctor;

create table checks(
check_id varchar(50) primary key,
patient_id varchar(50),
doctor_id varchar(50),
check_date date,
diagnosis varchar (50),
foreign key (patient_id) references patient(patient_id),
foreign key (doctor_id) references doctor(doctor_id)
);
select *from checks;

create table lab_tests(
 test_id varchar (50) primary key,
 check_id varchar (50),
 test_date date,
 test_name varchar (50),
 result varchar (50),
 foreign key (check_id) references checks (check_id)
 );
 select*from lab_tests;
 create table medication (
 medication_id varchar(50) primary key ,
 check_id varchar (50),
 manufacture  varchar (50),
 dosage varchar (50),
 medication_date date ,
 foreign key (check_id) references checks(check_id)
 );
 alter table medication drop medication_date;
 select * from medication;
 select *from  checks;
 create table visit(
 hospital_id varchar (50) ,
 patient_id varchar(50) ,
 visit_date date,
discharge_date date,
primary key(hospital_id , patient_id )
);
