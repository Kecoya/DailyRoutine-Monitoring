from fracDimPy import generate_sierpinski, generate_koch_snowflake
import matplotlib.pyplot as plt

# 生成Sierpinski三角形
sierpinski = generate_sierpinski(level=6)

# 生成Koch雪花
snowflake = generate_koch_snowflake(level=5)

# 可视化
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
ax1.scatter(sierpinski[:, 0], sierpinski[:, 1], s=1, c='blue')
ax1.set_title('Sierpinski Triangle')
ax1.axis('equal')

ax2.plot(snowflake[:, 0], snowflake[:, 1], 'r-', linewidth=0.5)
ax2.set_title('Koch Snowflake')
ax2.axis('equal')

plt.show()