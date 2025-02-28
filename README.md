# csvprocess
1.Sample CSV Format for upload where the image link should be working (products.csv):
  Serial Number|Product Name|Input Image Urls
  1|Chair|https://example.com/chair1.jpg,https://example.com/chair2.jpg
  2|Table|https://example.com/table.jpg

2. How to Use:
   Install Requirements:
    pip install flask flask-sqlalchemy requests pillow
3. Run the Application:
    python app.py

4. Upload CSV:
    curl -X POST -F "file=@products.csv" http://localhost:5000/upload
5. Check Status:
    curl http://localhost:5000/status/YOUR_REQUEST_ID
6. Access Processed Images:
  All compressed images will be available at:
    http://localhost:5000/output/FILENAME.jpg
