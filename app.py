import pandas as pd
import plotly.express as px
import streamlit as st

# 常量定义
COLOR_MAPPING = {
    4: '奇迹',
    8: '行动',
    9: '领袖',
    10: '农矿',
    11: '事件',
    12: '建筑',
    13: '部队',
    14: '政府',
    15: '蓝卡',
    16: '阵形',
    18: '侵略',
    21: '战争'
}

# 页面配置
st.set_page_config(
    page_title="卡牌胜率分析",
    layout="wide",
    initial_sidebar_state="auto"
)

# 自定义CSS样式
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 0rem;
    padding-left: 5rem;
    padding-right: 5rem;
}
.stDataFrame {
    width: 100% !important;
}
.css-1dj4j8c {
    max-width: 100% !important;
}

/* 新增卡片化设计 */
.css-1p05t8e {
    border-radius: 15px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    padding: 2rem;
    margin: 1rem 0;
    background: white;
}

/* 图表容器美化 */
.plot-container {
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    overflow: hidden;
}

/* 表格标题样式 */
h2 {
    color: #2c3e50 !important;
    border-bottom: 2px solid #3498db;
    padding-bottom: 0.5rem;
}

/* 侧边栏美化 */
[data-testid="stSidebar"] {
    background: linear-gradient(145deg, #f8f9fa 0%, #e9ecef 100%);
    padding: 1rem;
}
</style>
""", unsafe_allow_html=True)


# 数据预处理
@st.cache_data
def load_data():
    df = pd.read_csv('game_analysis.csv')  # 替换为实际文件名
    df['卡牌类型'] = df['颜色'].map(COLOR_MAPPING)
    df['轮次'] = df['轮次'].astype(int)
    df['花费'] = df['花费'].astype(int)
    return df.rename(columns={'中文名': '卡名'})


df = load_data()

# 侧边栏筛选
st.sidebar.header("筛选条件")
filters = [
    ('组别', st.sidebar.multiselect('组别', df['组别'].unique())),
    ('卡牌类型', st.sidebar.multiselect('卡牌类型', df['卡牌类型'].unique())),
    ('卡名', st.sidebar.multiselect('卡名', df['卡名'].unique())),
    ('行为', st.sidebar.multiselect('行为', df['行为'].unique())),
    ('先后', st.sidebar.multiselect('先后手', df['先后'].unique())),
    ('玩家', st.sidebar.multiselect('玩家', df['玩家'].unique()))
]

round_range = st.sidebar.slider(
    '轮次范围',
    min_value=int(df['轮次'].min()),
    max_value=int(df['轮次'].max()),
    value=(int(df['轮次'].min()), int(df['轮次'].max()))
)

cost_range = st.sidebar.slider(
    '花费范围',
    min_value=int(df['花费'].min()),
    max_value=int(df['花费'].max()),
    value=(int(df['花费'].min()), int(df['花费'].max()))
)

# 数据过滤
filtered_df = df[
    df['轮次'].between(*round_range) &
    df['花费'].between(*cost_range)
    ]

for col, values in filters:
    if values:
        filtered_df = filtered_df[filtered_df[col].isin(values)]


# 核心计算逻辑
def calculate_stats(group):
    wins = group[group['胜负'] == '赢']
    loses = group[group['胜负'] != '赢']

    dups = len(group.drop_duplicates(subset=['CODE', '玩家']))
    win_dups = len(wins.drop_duplicates(subset=['CODE', '玩家']))

    return pd.Series({
        '胜率': win_dups / dups if dups else 0,
        '总场数': dups,
        '胜场': win_dups,
        '负场': len(loses.drop_duplicates(subset=['CODE', '玩家'])),
        **{f'平均{k}': v.mean() for k, v in {
            '轮次': group['轮次'],
            '胜场轮次': wins['轮次'],
            '负场轮次': loses['轮次'],
            '花费': group['花费'],
            '胜场花费': wins['花费'],
            '负场花费': loses['花费']
        }.items()}
    })


# 主界面
st.title('卡牌胜率分析仪表盘')
control_cols = st.columns([2, 2, 4, 4])
with control_cols[0]:
    page_size = st.selectbox('每页显示行数', [5, 10, 20, 50, '全部'], index=1)

result = pd.DataFrame()
if not filtered_df.empty:
    with control_cols[2]:
        selected_dimensions = st.multiselect(
            '分析维度',
            ['卡名', '轮次', '行为', '花费', '玩家'],
            default=['卡名']
        )
    with control_cols[3]:
        sort_order = st.selectbox('排序方式', [
            '胜率降序', '胜率升序',
            '总场数降序', '总场数升序',
            '胜场降序', '胜场升序'
        ])

    if selected_dimensions:
        result = filtered_df.groupby(selected_dimensions).apply(calculate_stats).reset_index()
        result['维度组合'] = result[selected_dimensions].apply(lambda x: ' - '.join(x.astype(str)), axis=1)

        # 动态排序
        sort_config = {
            '胜率降序': ('胜率', False),
            '胜率升序': ('胜率', True),
            '总场数降序': ('总场数', False),
            '总场数升序': ('总场数', True),
            '胜场降序': ('胜场', False),
            '胜场升序': ('胜场', True)
        }[sort_order]
        print(result.columns)
        result = result.sort_values(by=sort_config[0], ascending=sort_config[1])

# 结果展示
if not result.empty:
    # 分页逻辑
    if page_size != '全部':
        with control_cols[1]:
            total_pages = (len(result) - 1) // page_size + 1
            current_page = st.selectbox('页码', range(1, total_pages + 1)) - 1
            paginated_df = result.iloc[current_page * page_size: (current_page + 1) * page_size]
    else:
        paginated_df = result

    # 使用渐变色样式
    styled_df = paginated_df.style.background_gradient(
        subset=['胜率'],
        cmap='RdYlGn',  # 红-黄-绿渐变色
        vmin=0,
        vmax=1
    ).format({
        '胜率': '{:.1%}',
        **{col: '{:.0f}' for col in result.columns if '场' in col},
        **{col: '{:.1f}' for col in result.columns if '平均' in col}
    })

    st.dataframe(styled_df, height=500, use_container_width=True, hide_index=True)

    # 可视化图表
    fig = px.bar(
        result,
        x='维度组合',
        y='胜率',
        color='胜率',
        color_continuous_scale='RdYlGn',
        range_color=[0, 1]
    )
    # 优化后的图表配置
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_family="Arial"
        ),
        xaxis=dict(
            showgrid=False,
            linecolor='#bdc3c7'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#ecf0f1',
            linecolor='#bdc3c7'
        ),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 显示原始数据（可选）
    if st.checkbox('显示原始数据'):
        st.write(filtered_df)
else:
    st.warning('当前筛选条件下无数据')