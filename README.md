# README
The `preprocess.py` file will examine uploaded tar files for validity, make a manifest, add entry into titledb, and move files into production.

## Configuration values
The default configuration keys are in `default-config.ini`. You will need to copy those into a local `config.ini` file and assign the values suited for your environment. Comments should be on different lines, and values should not use escape characters (no quotes)

# REQUIREMENTS:
requires pandas for html creation - pip install pandas
also requires droid: https://tna-cdn-live-uk.s3.eu-west-2.amazonaws.com/documents/droid-binary-6.8.0-bin.zip
droid uses java openjdk version 8 to 17, 17 tested here
droid needs to be updated periodically(daily?), create a cron job simular to the following: java -Xmx1024m -jar /PATH/TO/droid-command-line-6.8.0.jar -d