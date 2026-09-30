import os
import subprocess

smali_path = os.path.join("modding", "build_cache", "baksmali_multidex", "com", "nekki", "catblasters", "AssetExtractor.smali")

with open(smali_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
inserted_thread = False
for line in lines:
    if line.strip() == ".super Ljava/lang/Object;":
        out.append(line)
        out.append(".implements Ljava/lang/Runnable;\n")
    elif line.strip() == ":goto_0" and not inserted_thread:
        out.append("    :goto_0\n")
        out.append("    new-instance v0, Ljava/lang/Thread;\n")
        out.append("    new-instance v1, Lcom/nekki/catblasters/AssetExtractor;\n")
        out.append("    invoke-direct {v1}, Lcom/nekki/catblasters/AssetExtractor;-><init>()V\n")
        out.append("    invoke-direct {v0, v1}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V\n")
        out.append("    invoke-virtual {v0}, Ljava/lang/Thread;->start()V\n")
        inserted_thread = True
    else:
        out.append(line)

extra = """
.method public run()V
    .registers 11

    :try_start_loop
    :loop_activity
    sget-object v0, Lcom/unity3d/player/UnityPlayer;->currentActivity:Landroid/app/Activity;
    if-nez v0, :cond_activity_found

    const-wide/16 v0, 0x1f4
    invoke-static {v0, v1}, Ljava/lang/Thread;->sleep(J)V
    goto :loop_activity

    :cond_activity_found
    const-wide/16 v0, 0x1770
    invoke-static {v0, v1}, Ljava/lang/Thread;->sleep(J)V

    const/4 v2, 0x0
    :loop_tap
    const/4 v0, 0x3
    if-ge v2, v0, :cond_end

    invoke-static {}, Lcom/nekki/catblasters/AssetExtractor;->performTap()V

    const-wide/16 v0, 0x5dc
    invoke-static {v0, v1}, Ljava/lang/Thread;->sleep(J)V

    add-int/lit8 v2, v2, 0x1
    goto :loop_tap

    :cond_end
    :try_end_loop
    .catch Ljava/lang/Exception; {:try_start_loop .. :try_end_loop} :catch_err
    goto :goto_ret

    :catch_err
    move-exception v0

    :goto_ret
    return-void
.end method

.method private static performTap()V
    .registers 12

    :try_start_tap
    sget-object v0, Lcom/unity3d/player/UnityPlayer;->currentActivity:Landroid/app/Activity;
    if-nez v0, :cond_0
    return-void

    :cond_0
    invoke-virtual {v0}, Landroid/app/Activity;->getWindow()Landroid/view/Window;
    move-result-object v0
    if-nez v0, :cond_1
    return-void

    :cond_1
    invoke-virtual {v0}, Landroid/view/Window;->getDecorView()Landroid/view/View;
    move-result-object v0
    if-nez v0, :cond_2
    return-void

    :cond_2
    invoke-virtual {v0}, Landroid/view/View;->getWidth()I
    move-result v1
    invoke-virtual {v0}, Landroid/view/View;->getHeight()I
    move-result v2

    int-to-float v1, v1
    const v8, 0x3f5aa000 # 0.854f
    mul-float/2addr v8, v1

    int-to-float v2, v2
    const v9, 0x3f4e147b # 0.805f
    mul-float/2addr v9, v2

    invoke-static {}, Landroid/os/SystemClock;->uptimeMillis()J
    move-result-wide v3

    const/4 v7, 0x0
    const/4 v10, 0x0
    move-wide v5, v3
    invoke-static/range {v3 .. v10}, Landroid/view/MotionEvent;->obtain(JJIFFI)Landroid/view/MotionEvent;
    move-result-object v1
    invoke-virtual {v0, v1}, Landroid/view/View;->dispatchTouchEvent(Landroid/view/MotionEvent;)Z
    invoke-virtual {v1}, Landroid/view/MotionEvent;->recycle()V

    const-wide/16 v1, 0x32
    add-long v5, v3, v1
    const/4 v7, 0x1
    invoke-static/range {v3 .. v10}, Landroid/view/MotionEvent;->obtain(JJIFFI)Landroid/view/MotionEvent;
    move-result-object v1
    invoke-virtual {v0, v1}, Landroid/view/View;->dispatchTouchEvent(Landroid/view/MotionEvent;)Z
    invoke-virtual {v1}, Landroid/view/MotionEvent;->recycle()V

    const-string v0, "CatBlasters"
    const-string v1, "AutoFight: Dispatched tap on Fight button!"
    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_tap
    .catch Ljava/lang/Exception; {:try_start_tap .. :try_end_tap} :catch_tap

    goto :goto_tap_ret

    :catch_tap
    move-exception v0

    :goto_tap_ret
    return-void
.end method
"""

full_code = "".join(out) + extra

with open(smali_path, "w", encoding="utf-8") as f:
    f.write(full_code)

smali_jar = os.path.join("modding", "tools", "smali.jar")
baksmali_dir = os.path.join("modding", "build_cache", "baksmali_multidex")
classes_dex = os.path.join("modding", "build_cache", "test.dex")

res = subprocess.run(f'java -jar "{smali_jar}" a "{baksmali_dir}" -o "{classes_dex}"', shell=True, capture_output=True, text=True)
print("STDERR:", res.stderr)
print("Return code:", res.returncode)
