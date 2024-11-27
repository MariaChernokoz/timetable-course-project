DROP TABLE IF EXISTS JointEventParticipation;
DROP TABLE IF EXISTS JointEventRequests;
DROP TABLE IF EXISTS Events;
DROP TABLE IF EXISTS Regularity;
DROP TABLE IF EXISTS Tasks;
DROP TABLE IF EXISTS Friendships;
DROP TABLE IF EXISTS FriendRequest;
DROP TABLE IF EXISTS Users; 

DROP SCHEMA IF EXISTS TimetableMain;
DROP DATABASE IF EXISTS Timetable;

CREATE DATABASE Timetable;
CREATE SCHEMA TimetableMain;

CREATE TABLE Users (
 User_login VARCHAR(255) PRIMARY KEY,
 Password VARCHAR(255) NOT NULL
);

CREATE TABLE FriendRequest (
 Request_ID INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 Status_request VARCHAR(255) NOT NULL,
 Senders_login VARCHAR(255) NOT NULL REFERENCES Users (User_login),
 Recipient_login VARCHAR(255) NOT NULL REFERENCES Users (User_login)
);

CREATE TABLE Friendships (
 Friendship_ID INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 Senders_login VARCHAR(255) NOT NULL REFERENCES Users (User_login),
 Recipient_login VARCHAR(255) NOT NULL REFERENCES Users (User_login)
);

CREATE TABLE Tasks (
 TaskID INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 User_login VARCHAR(255) NOT NULL REFERENCES Users(User_login),
 Task_name VARCHAR(255) NOT NULL,
 Creation_date TIMESTAMP WITH TIME ZONE NOT NULL,
 Deadline TIMESTAMP WITH TIME ZONE,
 Task_status VARCHAR(255) NOT NULL
);

CREATE TABLE Regularity (
 Regularity_ID INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 Regularity_interval INTEGER NOT NULL,
 Days_of_week VARCHAR(14) NOT NULL, 
 End_date TIMESTAMP WITH TIME ZONE
);

CREATE TABLE Events (
 Event_ID INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 Event_name VARCHAR(255) NOT NULL,
 Start_time_and_date TIMESTAMP WITH TIME ZONE NOT NULL,
 End_time_and_date TIMESTAMP WITH TIME ZONE,
 Location VARCHAR(255),
 Category VARCHAR(255),
 Comment TEXT,
 Regularity_ID INTEGER REFERENCES Regularity(Regularity_ID)
);

CREATE TABLE JointEventRequests (
 Request_ID INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 Senders_login VARCHAR(255) NOT NULL REFERENCES Users(User_login),
 Recipient_login VARCHAR(255) NOT NULL REFERENCES Users(User_login),
 Event_name VARCHAR(255) NOT NULL,
Start_time_and_date TIMESTAMP WITH TIME ZONE NOT NULL,
 End_time_and_date TIMESTAMP WITH TIME ZONE,
 Regularity_ID INTEGER REFERENCES Regularity(Regularity_ID),
 Location VARCHAR(255),
 Category VARCHAR(255),
 Comment TEXT,
 Request_status VARCHAR(255) NOT NULL
);
CREATE TABLE JointEventParticipation (
 Event_ID INTEGER NOT NULL REFERENCES Events(Event_ID),
 User_login VARCHAR(255) NOT NULL REFERENCES Users(User_login),
 PRIMARY KEY (Event_ID, User_login)
);
