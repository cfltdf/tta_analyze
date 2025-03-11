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
    15: '蓝科',
    16: '阵形',
    18: '侵略',
    21: '战争'
}


# 数据预处理
@st.cache_resource
class GameAnalyze:
    def __init__(self):
        self.df = self._load_df()
        self.multi_filters = {col: self.df[col].unique() for col in ['组别', '类型', '卡名', '行为', '先后', '玩家']}
        self.range_filters = {col: (self.df[col].min(), self.df[col].max()) for col in ['轮次', '花费']}

    @staticmethod
    def _load_df():
        dtypes = {
            '颜色': 'int8',
            '轮次': 'int16',
            '花费': 'int16',
            '胜负': 'category',
            'CODE': 'category',
            '玩家': 'category',
            '中文名': 'category'
        }
        df = pd.read_csv('game_analysis.csv', dtype=dtypes)
        df['类型'] = df['颜色'].map(COLOR_MAPPING).astype('category')
        df = df.rename(columns={'中文名': '卡名'})
        return df


def render_config():
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
        papding-top: 1rem;
        papding-bottom: 0rem;
        papding-left: 5rem;
        papding-right: 5rem;
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
        papding: 2rem;
        margin: 1rem 0;
        background: white;
    }
    
    /* 图表容器美化 */
    .plot-container {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        overflow: hipden;
    }
    
    /* 表格标题样式 */
    h2 {
        color: #2c3e50 !important;
        border-bottom: 2px solid #3498db;
        papding-bottom: 0.5rem;
    }
    
    /* 侧边栏美化 */
    [data-testid="stSidebar"] {
        background: linear-gradient(145deg, #f8f9fa 0%, #e9ecef 100%);
        papding: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_filter(df, **kwargs):
    with st.spinner("正在处理数据，请稍候..."):
        filter_mask = pd.Series(True, index=df.index)
        for col, (filter_type, values) in kwargs.items():
            if filter_type == 'multi':
                if values:
                    filter_mask &= df[col].isin(values)
            elif filter_type == 'range':
                filter_mask &= df[col].between(*values)
        return df[filter_mask]


@st.cache_data(ttl=3600, show_spinner=False)
def cached_groupby(df, dimensions):
    with st.spinner("正在处理数据，请稍候..."):
        result = df.groupby(dimensions).apply(calculate_stats).reset_index()
        result = result[result.总场数 > 0]
        print(result)
        return result


def render_filter(ga: GameAnalyze):
    # 侧边栏筛选
    st.sidebar.header("筛选条件")

    df = ga.df.copy()
    filter_args = dict()
    for col, multi_filter in ga.multi_filters.items():
        filter_args[col] = 'multi', st.sidebar.multiselect(col, multi_filter)

    for col, (min_value, max_value) in ga.range_filters.items():
        filter_args[col] = 'range', st.sidebar.slider(
            f'{col}范围',
            min_value=int(min_value),
            max_value=int(max_value),
            value=(int(min_value), int(max_value))
        )

    return cached_filter(df, **filter_args)


# 核心计算逻辑
def calculate_stats(group):
    base_groups = {
        '总场': pd.Series(True, index=group.index),
        '胜场': group['胜负'].eq('赢'),
        '负场': group['胜负'].ne('赢')
    }
    unique_counts = {
        name: group.loc[mask, ['CODE', '玩家']].drop_duplicates().shape[0]
        for name, mask in base_groups.items()
    }

    return pd.Series({
        '胜率': unique_counts['胜场'] / unique_counts['总场'] if unique_counts['总场'] > 0 else 0,
        **{f'{k}数': v for k, v in unique_counts.items()},
        **{f'{k}平均{stat}': group.loc[mask, stat].mean()
           for stat in ['轮次', '花费']
           for k, mask in base_groups.items()},
    })


def render_table(result):
    # 使用渐变色样式
    styled_df = result.style.background_gradient(
        subset=['胜率'],
        cmap='RdYlGn',  # 红-黄-绿渐变色
        vmin=0,
        vmax=1
    ).format({
        '胜率': '{:.1%}',
        **{col: '{:.0f}' for col in result.columns if col[-1] == '数'},
        **{col: '{:.1f}' for col in result.columns if '平均' in col}
    })

    styled_df.hide_index_ = True
    styled_df.hidden_columns = [len(styled_df.data.columns) - 1]
    st.dataframe(styled_df, height=400, use_container_width=True, hide_index=True)


def render_graph(df):
    # 可视化图表
    fig = px.bar(
        df,
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
    # 动态添加文本标签
    if len(df) < 100:
        fig.update_traces(
            text=df['胜率'].apply(lambda x: f"{x:.1%}"),
            textposition='inside',
            textfont=dict(size=12, color='#333')
        )

    # 添加点击事件
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "胜率: %{y:.1%}<br>"
            "总场数: %{customdata[0]}<br>"
            "胜场数: %{customdata[1]}"
        ),
        customdata=df[['总场数', '胜场数']].values
    )
    st.plotly_chart(fig, use_container_width=True)


def render_pagination(result, page_size, control):
    # 分页逻辑
    total_pages = (len(result) - 1) // page_size + 1
    if total_pages > 1:
        current_page = control.number_input('页码', min_value=1, max_value=total_pages) - 1
        return result.iloc[current_page * page_size: (current_page + 1) * page_size]
    return result


def render_main(df):
    # 主界面
    st.title('历史巨轮卡牌胜率统计')
    st.subheader('统计范围：Royal League S1-S3, Premier League S1-S4')
    control_cols = st.columns([2, 2, 4, 2, 2])
    page_size = control_cols[0].selectbox('每页显示行数', [5, 10, 20, 50, 100], index=1)

    ANAL_DIMS = ['卡名', '行为', '先后', '轮次', '花费', '玩家']

    result = pd.DataFrame()
    if not df.empty:
        selected_dimensions = control_cols[2].multiselect('分析维度', ANAL_DIMS, default=['卡名'])
        sort_order = control_cols[3].selectbox('排序依据', ['胜率', '总场数', '胜场数'])
        sort_type = control_cols[4].selectbox('排序方式', ['降序', '升序'])

        if selected_dimensions:
            result = cached_groupby(df, selected_dimensions)
            result['维度组合'] = result[selected_dimensions].apply(lambda x: ' - '.join(x.astype(str)), axis=1)
            result = result.sort_values(by=sort_order, ascending=sort_type == '升序')

    # 结果展示
    if not result.empty:
        paginated_result = render_pagination(result, page_size, control_cols[1])
        render_table(paginated_result)
        render_graph(result)
        # 显示原始数据（可选）
        if st.checkbox('显示原始数据'):
            st.write(df)
    else:
        st.warning('当前筛选条件下无数据')


def render(ga: GameAnalyze):
    df = render_filter(ga)
    render_main(df)


render(GameAnalyze())
