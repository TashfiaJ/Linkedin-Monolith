import time
from fastapi import APIRouter, FastAPI, HTTPException, UploadFile, Form, File, BackgroundTasks, Depends, Query
from pydantic import BaseModel
from model import User, POSTS, PostCreation, Notification
from config import user_collection1, user_collection2, user_collection3, db1, db2, db3  # Import the user collection reference
import JWTtoken
from datetime import datetime
from minio import Minio
import io
import uuid
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

import requests
from schema import postSchema, postsSchema, notificationsEntity
from bson import ObjectId
import json
import asyncio


router=APIRouter()

# Create a Minio client with the configured HTTP client
minio_client = Minio(
    "127.0.0.1:9000",
    access_key="JMj2sjw7Pr0SH0qquzjl",
    secret_key="vl9UYf1YuABbxmtuPm26lE2a9M1siVExSuFz0VjA",
    secure=False  # Change to True if using HTTPS
)

async def upload_image(imgFile, username: str):
    bucket_name = "linkedin"
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
    file_bytes = await imgFile.read()
    unique_filename = username + str(uuid.uuid4()) + "_" + imgFile.filename
    file_stream = io.BytesIO(file_bytes)

    minio_client.put_object(
        "linkedin",
        unique_filename,
        file_stream,
        length=len(file_bytes),
        content_type=imgFile.content_type,
    )

    presigned_url = minio_client.presigned_get_object('linkedin', unique_filename)
    print(presigned_url)
    return presigned_url

# API to create a new user
@router.post("/user/create")
async def create_user(user_data: User):
    # Check if the user already exists
    if user_collection1.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Insert the user data into the MongoDB collection
    user_collection1.insert_one(user_data.dict())
    print("Ki hoitese")
    return {"message": "User created successfully"}

# API for user login
@router.post("/user/login")
async def login_user(user_data: User):
    user = user_collection1.find_one({"username": user_data.username, "email": user_data.email, "password": user_data.password})
    if user is None:
        raise HTTPException(status_code=401, detail="Login failed. Invalid credentials")

    access_token = JWTtoken.create_access_token(data={"sub": user_data.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/post/getpost", response_model=list[POSTS])
async def get_posts(user_id: str):
    # print(user_id)
    try:
        # Filter out posts by the logged-in user
        posts = user_collection2.find({"username": {"$ne": user_id}})
        post_list = postsSchema(posts)
        # print(post_list)
        return post_list
    except Exception as error:
        print(error)
        raise HTTPException(status_code=500, detail="Internal server error")
    

@router.get("/post/gettimeline", response_model=list[POSTS])
async def get_timeline(user_id: str):
    print(user_id)
    try:
        # Filter out posts by the logged-in user
        posts = user_collection2.find({"username": user_id})
        post_list = postsSchema(posts)
        print(post_list)
        return post_list
    except Exception as error:
        print(error)
        raise HTTPException(status_code=500, detail="Internal server error")
    

@router.get('/post/{postId}', response_model=POSTS)
async def get_post(postId: str):
    try:
        post = user_collection2.find_one({"_id": ObjectId(postId)})
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        return postSchema(post)
    except Exception as error:
        print(error)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/post/create")
async def add_post(username: str=Form(None),
    texts: str = Form(None),
    image_file: UploadFile = File(None)):
    try:
        image_url=""
        if image_file:
            image_url = await upload_image(image_file, username)
        result = user_collection2.insert_one({
            "username": username,
            "texts": texts,
            "image_url": image_url
        })
        post_id = result.inserted_id

        # Create notification message
        message = "Added an image!"
        if texts:
            message = texts[:70]

        # current_time = datetime.now().isoformat()
        # print("curr", current_time)

        # notification_data = {
        #     "username": username,
        #     "timeStamp": current_time,
        # }
        # notification_api_url = "http://localhost:8000/notification/create_notification/"  # Replace with the actual URL of the Notification Microservice
        # response = requests.post(notification_api_url, json=notification_data)

        # if response.status_code == 200:
        #     print("Notification created successfully")
        # else:
        #     print("Failed to create notification")

        current_time = datetime.now().isoformat()

        # Create the notification data
        notification_data = Notification(username=username, timeStamp=current_time)

        # Insert the notification directly into the collection
        result = user_collection3.insert_one(notification_data.dict())

        # if result.acknowledged:
        #     return {"message": "Notification created successfully"}
        # else:
        #     return {"message": "Failed to create notification"}


    except Exception as error:
        print(error)
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"message": "Post created successfully"}

# Define your proxy configuration (assuming this is needed for Minio)
proxy_host = 'minio'
proxy_port = 9000

# Create an HTTP client session with proxy settings
from urllib3 import make_headers
from urllib3 import ProxyManager

proxy_headers = make_headers(proxy_basic_auth='username:password')  # If your proxy requires authentication
http_client = ProxyManager(
    proxy_url=f"http://{proxy_host}:{proxy_port}",
    proxy_headers=proxy_headers
)


@router.post("/notification/create_notification")
async def create_notification(notification: Notification):
    print(notification)
    try:
        result = user_collection3.insert_one(notification.dict())

        if result.acknowledged:
            return {"message": "Notification created successfully"}
        else:
            return {"message": "Failed to create notification"}
    except Exception as error:
        print(error)
        return {"message": "Failed to create notification"}


@router.get("/notification/get_notification", response_model=list[str])
def get_notifications(user_id: str):
    print(user_id)
    try:
        filtered_notifications = user_collection3.find({"username": {"$ne": user_id}})
        notification_list = list(filtered_notifications)

        current_timestamp = datetime.now()  # Get the current timestamp in seconds
        formatted_messages = []

        for notification in notification_list:
            timestamp = notification["timeStamp"]
            # timestamp_seconds = int(timestamp.timestamp())  # Convert the timestamp to seconds
            # print("timestamp-second", timestamp_seconds)
            time_elapsed = (current_timestamp.timestamp() - timestamp.timestamp())
            minutes_elapsed = int(time_elapsed // 60)
            formatted_message = f"{notification['username']} has posted {minutes_elapsed} minutes ago"
            formatted_messages.append(formatted_message)

        return formatted_messages
    except Exception as error:
        print(error)
        raise HTTPException(status_code=500, detail="Internal server error")

def delete_old_notifications():
    # Get all notifications from the collection
    all_notifications = user_collection3.find()  # Get the current timestamp in seconds
    deleted_count = 0

    for notification in all_notifications:
        timestamp = notification["timeStamp"]
        current_timestamp = datetime.now()
        time_elapsed = current_timestamp.timestamp() - timestamp.timestamp()
        minutes_elapsed = int(time_elapsed // 60)
        if minutes_elapsed >= 30:
            # Delete the notification if it's older than 30 minutes
            user_collection3.delete_one({"_id": notification["_id"]})
            deleted_count += 1

    print(f"Deleted {deleted_count} notifications older than 30 minutes")

@router.get("/notification/cleanup_notifications")
def cleanup_notifications():
    # Schedule the cleanup task to run in the background
    delete_old_notifications()
    return {"message": "Cleanup task scheduled"}

scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_notifications, 'interval', minutes=5)
scheduler.start()





