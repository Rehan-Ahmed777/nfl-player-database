# NFL Dynasty Hub - Deployment Guide

## Deploy to Render.com (FREE)

### Step 1: Prepare Your Code
1. Create a GitHub repository (or use GitLab/Bitbucket)
2. Push all files from `C:\Users\rehan\Desktop\NFL PLAYER` to the repository

### Step 2: Deploy on Render
1. Go to https://render.com
2. Sign up/Login (you can use GitHub to login)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Configure:
   - **Name:** `nfl-dynasty-hub` (or your preferred name)
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Plan:** Free
6. Click "Create Web Service"

### Step 3: Wait for Deployment
- Render will build and deploy your app (takes 2-5 minutes)
- Your app will be available at: `https://nfl-dynasty-hub.onrender.com`

### Important Notes:
- **Free tier sleeps after 15 minutes of inactivity** (first load will be slow)
- **No credit card required** for free tier
- **Automatic HTTPS** included
- **Auto-deploy** on every git push

### Alternative: Manual Deploy (No Git Required)

If you don't want to use Git:

1. Go to Render.com → New → Web Service
2. Choose "Build and deploy from a Git repository"
3. Or use Render's manual upload option

### Environment Variables (Optional)
If needed, you can set environment variables in Render dashboard:
- Go to your service → Environment
- Add any API keys or secrets

### Your App URL
After deployment, your app will be accessible at:
**https://nfl-dynasty-hub.onrender.com** (or whatever name you choose)

### Sharing with Friends
Just share the URL! No authentication needed - it's a public web app.
If you want to add password protection later, let me know.

---

## Troubleshooting

### If deployment fails:
1. Check the build logs in Render dashboard
2. Verify all files are in the repository
3. Make sure requirements.txt has all dependencies

### If app is slow:
- Free tier sleeps after inactivity
- First request after sleep takes 30-60 seconds
- Consider upgrading to paid tier ($7/month) for always-on

---

## Next Steps After Deployment

Once deployed, test with:
1. Your Sleeper username
2. Your league ID
3. Try the filters and refresh functionality

Let me know if you encounter any issues!
