"""
Chart components using Plotly for interactive visualizations.
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Optional, Dict
import streamlit as st


def create_metric_chart(
    df: pd.DataFrame,
    metric_name: str,
    title: Optional[str] = None,
    show_rolling: bool = False,
    benchmark_df: Optional[pd.DataFrame] = None
) -> go.Figure:
    """
    Create an interactive line chart for a metric.

    Args:
        df: DataFrame with timestamp index and metric columns
        metric_name: Name of the metric column to plot
        title: Chart title
        show_rolling: Whether to show rolling average line
        benchmark_df: Optional benchmark data to overlay

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    if metric_name not in df.columns:
        st.warning(f"Metric '{metric_name}' not found in data")
        return fig

    # Main metric line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df[metric_name],
        mode='lines',
        name=metric_name,
        line=dict(color='#1f77b4', width=2),
        hovertemplate='%{x|%Y-%m-%d}<br>%{y:.2f}<extra></extra>'
    ))

    # Rolling average if requested
    if show_rolling and f"{metric_name}_ma" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[f"{metric_name}_ma"],
            mode='lines',
            name=f"{metric_name} (MA)",
            line=dict(color='#ff7f0e', width=2, dash='dash'),
            hovertemplate='%{x|%Y-%m-%d}<br>%{y:.2f}<extra></extra>'
        ))

    # Benchmark if provided
    if benchmark_df is not None and metric_name in benchmark_df.columns:
        fig.add_trace(go.Scatter(
            x=benchmark_df.index,
            y=benchmark_df[metric_name],
            mode='lines',
            name=f"{metric_name} (Benchmark)",
            line=dict(color='#2ca02c', width=2, dash='dot'),
            hovertemplate='%{x|%Y-%m-%d}<br>%{y:.2f}<extra></extra>'
        ))

    # Update layout
    fig.update_layout(
        title=title or f"{metric_name} Over Time",
        xaxis_title="Date",
        yaxis_title=metric_name,
        hovermode='x unified',
        template='plotly_white',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    fig.update_xaxes(
        rangeslider_visible=False,
        showgrid=True,
        gridwidth=1,
        gridcolor='LightGray'
    )

    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='LightGray'
    )

    return fig


def create_multi_metric_chart(
    df: pd.DataFrame,
    metrics: List[str],
    title: Optional[str] = None,
    normalize: bool = False
) -> go.Figure:
    """
    Create a chart with multiple metrics on the same axes.

    Args:
        df: DataFrame with timestamp index and metric columns
        metrics: List of metric names to plot
        title: Chart title
        normalize: Whether to normalize all metrics to start at 100

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    colors = px.colors.qualitative.Plotly

    for i, metric in enumerate(metrics):
        if metric not in df.columns:
            continue

        data = df[metric].dropna()
        if data.empty:
            continue

        # Normalize if requested
        if normalize and len(data) > 0:
            plot_data = (data / data.iloc[0]) * 100
            y_label = f"{metric} (Indexed)"
        else:
            plot_data = data
            y_label = metric

        fig.add_trace(go.Scatter(
            x=data.index,
            y=plot_data,
            mode='lines',
            name=metric,
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate='%{x|%Y-%m-%d}<br>%{y:.2f}<extra></extra>'
        ))

    fig.update_layout(
        title=title or "Multiple Metrics Comparison",
        xaxis_title="Date",
        yaxis_title="Value" + (" (Indexed to 100)" if normalize else ""),
        hovermode='x unified',
        template='plotly_white',
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    fig.update_xaxes(
        rangeslider_visible=False,
        showgrid=True,
        gridwidth=1,
        gridcolor='LightGray'
    )

    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='LightGray'
    )

    return fig


def create_distribution_chart(
    values: Dict[str, float],
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a bar chart showing distribution of values across symbols.

    Args:
        values: Dict mapping symbol to value
        title: Chart title

    Returns:
        Plotly Figure object
    """
    symbols = list(values.keys())
    vals = list(values.values())

    fig = go.Figure(data=[
        go.Bar(
            x=symbols,
            y=vals,
            marker_color='#1f77b4',
            hovertemplate='%{x}<br>%{y:.2f}<extra></extra>'
        )
    ])

    fig.update_layout(
        title=title or "Value Distribution",
        xaxis_title="Symbol",
        yaxis_title="Value",
        template='plotly_white',
        height=400,
        showlegend=False
    )

    fig.update_xaxes(
        showgrid=False
    )

    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='LightGray'
    )

    return fig


def create_comparison_chart(
    df: pd.DataFrame,
    metric_name: str,
    symbols: List[str],
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a chart comparing a metric across multiple symbols.

    Args:
        df: DataFrame with multi-level columns (symbol, metric)
        metric_name: Name of the metric to compare
        symbols: List of symbols to include
        title: Chart title

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    colors = px.colors.qualitative.Plotly

    for i, symbol in enumerate(symbols):
        # This assumes df has structure where we can access symbol-specific data
        # Adjust based on actual data structure
        if symbol in df.columns:
            symbol_data = df[symbol]
            if metric_name in symbol_data.columns:
                data = symbol_data[metric_name].dropna()

                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data,
                    mode='lines',
                    name=symbol,
                    line=dict(color=colors[i % len(colors)], width=2),
                    hovertemplate='%{x|%Y-%m-%d}<br>%{y:.2f}<extra></extra>'
                ))

    fig.update_layout(
        title=title or f"{metric_name} Comparison",
        xaxis_title="Date",
        yaxis_title=metric_name,
        hovermode='x unified',
        template='plotly_white',
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    fig.update_xaxes(
        rangeslider_visible=False,
        showgrid=True,
        gridwidth=1,
        gridcolor='LightGray'
    )

    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='LightGray'
    )

    return fig


def create_heatmap(
    df: pd.DataFrame,
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a correlation heatmap for metrics.

    Args:
        df: DataFrame with metrics as columns
        title: Chart title

    Returns:
        Plotly Figure object
    """
    # Calculate correlation matrix
    corr = df.corr()

    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.columns,
        colorscale='RdBu',
        zmid=0,
        text=corr.values,
        texttemplate='%{text:.2f}',
        textfont={"size": 10},
        hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.2f}<extra></extra>'
    ))

    fig.update_layout(
        title=title or "Metric Correlation Heatmap",
        template='plotly_white',
        height=500,
        width=600
    )

    return fig
