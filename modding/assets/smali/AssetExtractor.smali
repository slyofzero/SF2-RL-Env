.class public Lcom/nekki/catblasters/AssetExtractor;
.super Ljava/lang/Object;
.source "AssetExtractor.java"

# direct methods
.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static extractIfNeeded(Landroid/content/Context;)V
    .registers 9

    :try_start_0
    const/4 v0, 0x0
    invoke-virtual {p0, v0}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    move-result-object v0

    if-nez v0, :cond_0

    new-instance v0, Ljava/io/File;
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    const-string v2, "/sdcard/Android/data/"
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {p0}, Landroid/content/Context;->getPackageName()Ljava/lang/String;
    move-result-object v2
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v2, "/files"
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1
    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    :cond_0
    # 1. Check if bundles exist
    new-instance v1, Ljava/io/File;
    const-string v2, "gamedata/.all_packs_v2"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v1}, Ljava/io/File;->exists()Z
    move-result v2
    if-eqz v2, :cond_1
    goto :goto_user_check

    :cond_1
    const-string v1, "CatBlasters"
    const-string v2, "Extracting offline bundles from APK assets..."
    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    const-string v1, "gamedata/bundles/ANIMATIONS"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/VERSIONAL_CONFIGS"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/VERSIONAL_ASSETS"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/ZONE_1"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/ZONE_2"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/ZONE_3"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/ZONE_4"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/ZONE_5"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/ZONE_6"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/ZONE_7"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/ZONE_7_2"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/ZONE_7_3"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/ZONE_IM"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/EVENTS/EVENTS_COMMON"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/EVENTS/MA_FEST_26"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/EVENTS/SUMMER_FEST_25"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/EVENTS/SUMMER_FEST_26"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/EVENTS/SUMMER_FEST_CHEST"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/AGNISSEAL_OFFER"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLYOFFER12"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLY_OFFER_13"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLY_OFFER_14"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLY_OFFER_15"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLY_OFFER_16"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLY_OFFER_17"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLY_OFFER_18"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLY_OFFER_19"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLY_OFFER_20_FUTURIST_MAGIC"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLY_OFFER_21"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/bundles/OFFERS/WEEKLY_OFFER_22_GLAIVE_GOD_EATER"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/packs.xml"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/packs.xml.hash"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/config_cdn.xml"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "gamedata/config_cdn.xml.hash"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    new-instance v1, Ljava/io/File;
    const-string v2, "gamedata/.all_packs_v2"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->createNewFile()Z

    :goto_user_check
    # 2. Check if userdata/.provisioned_v4 exists
    new-instance v1, Ljava/io/File;
    const-string v2, "userdata/.provisioned_v4"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v1}, Ljava/io/File;->exists()Z
    move-result v2
    if-eqz v2, :cond_2
    const-string v0, "CatBlasters"
    const-string v1, "User profile v4 already present. Skipping profile extraction."
    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    goto :goto_0

    :cond_2
    const-string v1, "CatBlasters"
    const-string v2, "Extracting pre-configured user profile (skipping tutorial)..."
    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    const-string v1, "userdata/users.xml"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "userdata/users.xml.hash"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "userdata/users_backup.xml"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "userdata/users_backup.xml.hash"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "userdata/localSettings.bin"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "userdata/localSettings.bin.hash"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "userdata/initSettings.bin"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "userdata/gamingServiceSettings.bin"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    const-string v1, "userdata/gamingServiceSettings.bin.hash"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    new-instance v1, Ljava/io/File;
    const-string v2, "userdata/.provisioned_v4"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->createNewFile()Z

    const-string v0, "CatBlasters"
    const-string v1, "Offline bundles and tutorial skip profile ready!"
    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    goto :goto_0

    :catch_0
    move-exception v0
    const-string v1, "CatBlasters"
    const-string v2, "Error during asset extraction"
    invoke-static {v1, v2, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    :goto_0
    :try_start_frida
    const-string v1, "frida-gadget"
    invoke-static {v1}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V

    const-string v1, "CatBlasters"
    const-string v2, "Frida Gadget loaded successfully!"
    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_frida
    .catch Ljava/lang/Throwable; {:try_start_frida .. :try_end_frida} :catch_frida

    goto :goto_frida_end

    :catch_frida
    move-exception v1
    const-string v2, "CatBlasters"
    const-string v3, "Frida Gadget failed to load"
    invoke-static {v2, v3, v1}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    :goto_frida_end
    return-void
.end method
.method private static copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V
    .registers 9

    :try_start_0
    new-instance v0, Ljava/io/File;
    invoke-direct {v0, p1, p2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v0}, Ljava/io/File;->getParentFile()Ljava/io/File;
    move-result-object v1
    if-eqz v1, :cond_0
    invoke-virtual {v1}, Ljava/io/File;->mkdirs()Z

    :cond_0
    invoke-virtual {p0}, Landroid/content/Context;->getAssets()Landroid/content/res/AssetManager;
    move-result-object v1
    invoke-virtual {v1, p2}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;
    move-result-object v1

    new-instance v2, Ljava/io/FileOutputStream;
    invoke-direct {v2, v0}, Ljava/io/FileOutputStream;-><init>(Ljava/io/File;)V

    const/high16 v3, 0x10000
    new-array v3, v3, [B

    :goto_0
    invoke-virtual {v1, v3}, Ljava/io/InputStream;->read([B)I
    move-result v4
    const/4 v5, -0x1
    if-eq v4, v5, :cond_1
    const/4 v5, 0x0
    invoke-virtual {v2, v3, v5, v4}, Ljava/io/OutputStream;->write([BII)V
    goto :goto_0

    :cond_1
    invoke-virtual {v2}, Ljava/io/OutputStream;->flush()V
    invoke-virtual {v2}, Ljava/io/OutputStream;->close()V
    invoke-virtual {v1}, Ljava/io/InputStream;->close()V

    const-string v1, "CatBlasters"
    new-instance v2, Ljava/lang/StringBuilder;
    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V
    const-string v3, "Extracted asset: "
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v2
    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    goto :goto_1

    :catch_0
    move-exception v0
    const-string v1, "CatBlasters"
    new-instance v2, Ljava/lang/StringBuilder;
    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V
    const-string v3, "Failed to copy asset "
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v2
    invoke-static {v1, v2, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    :goto_1
    return-void
.end method

