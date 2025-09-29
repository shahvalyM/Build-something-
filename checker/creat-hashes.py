import hashlib
# File to creat hashes(sha-1) from the leaket password
with open('row_common_passwords.txt', 'r') as infile, open('leaked_password_hashes.txt', 'w') as outfile:
    for line in infile:
        password = line.strip()
        if password:  # Don't count the empty lines
            sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
            outfile.write(sha1 + '\n')