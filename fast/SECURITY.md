# Security Guidelines

## Environment Variables

### ⚠️ NEVER commit `.env` files to version control!

Your `.env` file contains sensitive credentials:
- MongoDB connection strings with passwords
- API keys (Voyage AI, OpenAI, etc.)
- Other secrets

## Setup Instructions for New Developers

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Fill in real credentials:**
   - Get MongoDB URI from your team lead or MongoDB Atlas dashboard
   - Get Voyage AI key from https://dashboard.voyageai.com/
   - Get OpenAI key from https://platform.openai.com/api-keys

3. **Verify `.env` is ignored:**
   ```bash
   git status --ignored | grep .env
   ```
   You should see `.env` in the ignored files list.

## If You Accidentally Commit Secrets

If you accidentally commit secrets to Git:

1. **Rotate credentials immediately:**
   - MongoDB: Change password in Atlas
   - Voyage AI: Regenerate API key
   - OpenAI: Regenerate API key

2. **Remove from Git history:**
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **Force push (coordinate with team):**
   ```bash
   git push origin --force --all
   ```

## Best Practices

- ✅ Use `.env.example` for documentation (no real secrets)
- ✅ Keep `.env` in `.gitignore`
- ✅ Rotate credentials regularly
- ✅ Use different credentials for dev/staging/production
- ❌ Never hardcode secrets in source code
- ❌ Never share `.env` files via email/chat
- ❌ Never commit `.env` files
