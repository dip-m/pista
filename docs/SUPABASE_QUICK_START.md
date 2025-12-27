# Supabase Quick Start

## Connection String

Your Supabase connection string:
```
postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres
```

## Quick Setup Steps

### 1. Test Connection

```bash
python update_utils/test_supabase_connection.py
```

If connection fails with DNS error:
- Verify connection string in Supabase dashboard (Settings → Database)
- Check if project is active
- Try from different network

### 2. Update Local `.env`

```env
DB_TYPE=postgres
DATABASE_URL=postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres
```

### 3. Run Migration

```bash
python update_utils/migrate_to_postgres.py \
  --sqlite-db gen/bgg_semantic.db \
  --postgres-url "postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres"
```

### 4. Configure Render

In Render dashboard → Environment Variables:
- Set `DATABASE_URL` to the Supabase connection string above
- Set `DB_TYPE=postgres`

## Getting Correct Connection String from Supabase

1. Go to [Supabase Dashboard](https://app.supabase.com/)
2. Select your project
3. Go to **Settings** → **Database**
4. Look for **"Connection string"** section
5. Copy the **"URI"** format connection string
6. It might look like:
   - `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres` (Pooling)
   - `postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres` (Direct)

**Note**: Supabase provides different connection strings:
- **Direct connection**: Port 5432 (for migrations, admin tools)
- **Connection pooling**: Port 6543 (for applications, better for production)

For migration, use the **Direct connection** (port 5432).
For Render deployment, you can use either, but pooling (6543) is recommended.

## If DNS Resolution Fails

If you get "could not translate host name" error:

1. **Verify the hostname** in Supabase dashboard
2. **Check your network** - Try from different network/VPN
3. **Use IP address** if available (check Supabase docs)
4. **Contact Supabase support** if project is new and DNS hasn't propagated

## Next Steps

Once connection works:
1. ✅ Run migration
2. ✅ Test locally
3. ✅ Set DATABASE_URL in Render
4. ✅ Deploy

See `SUPABASE_SETUP.md` for detailed guide.
