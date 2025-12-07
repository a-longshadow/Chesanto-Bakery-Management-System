#!/usr/bin/env python
"""Update report templates to use BEM classes."""
import os
import re

BASE = "apps/reports/templates/reports"

def update_production_daily():
    path = f"{BASE}/production/daily.html"
    content = '''{% extends "reports/base_reports.html" %}
{% load humanize %}

{% block reports_content %}
<!-- Page Header -->
<div class="page-header">
    <div class="page-header__content">
        <div class="page-header__title-group">
            <h1 class="page-header__title">
                <i class="bi bi-calendar-day"></i>
                Daily Production Report
            </h1>
            <p class="page-header__subtitle">{{ report_date|date:"l, F j, Y" }}</p>
        </div>
        <div class="nav-controls">
            <a href="?date={{ prev_date|date:'Y-m-d' }}" class="nav-controls__btn">
                <i class="bi bi-chevron-left"></i> Previous
            </a>
            {% if next_date %}
            <a href="?date={{ next_date|date:'Y-m-d' }}" class="nav-controls__btn">
                Next <i class="bi bi-chevron-right"></i>
            </a>
            {% else %}
            <span class="nav-controls__btn nav-controls__btn--disabled">
                Next <i class="bi bi-chevron-right"></i>
            </span>
            {% endif %}
        </div>
    </div>
</div>

<!-- KPI Cards -->
<div class="row g-3 mb-4">
    <div class="col-md-3">
        <div class="stat-card stat-card--primary">
            <div class="stat-card__icon"><i class="bi bi-layers"></i></div>
            <div class="stat-card__content">
                <span class="stat-card__label">Total Batches</span>
                <span class="stat-card__value">{{ batch_count }}</span>
                <span class="stat-card__meta">Production runs</span>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card stat-card--success">
            <div class="stat-card__icon"><i class="bi bi-box-seam"></i></div>
            <div class="stat-card__content">
                <span class="stat-card__label">Units Produced</span>
                <span class="stat-card__value">{{ total_quantity|intcomma }}</span>
                <span class="stat-card__meta">Total output</span>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card stat-card--warning">
            <div class="stat-card__icon"><i class="bi bi-currency-exchange"></i></div>
            <div class="stat-card__content">
                <span class="stat-card__label">Production Cost</span>
                <span class="stat-card__value">KES {{ total_cost|floatformat:0|intcomma }}</span>
                <span class="stat-card__meta">Estimated cost</span>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card stat-card--info">
            <div class="stat-card__icon"><i class="bi bi-grid"></i></div>
            <div class="stat-card__content">
                <span class="stat-card__label">Products</span>
                <span class="stat-card__value">{{ product_count }}</span>
                <span class="stat-card__meta">Unique items</span>
            </div>
        </div>
    </div>
</div>

<!-- Product Breakdown -->
<div class="report-section mb-4">
    <div class="report-section__header">
        <h3 class="report-section__title"><i class="bi bi-box-seam"></i> Production by Product</h3>
    </div>
    <div class="report-section__body p-0">
        {% if product_breakdown %}
        <table class="data-table">
            <thead>
                <tr>
                    <th>Product</th>
                    <th class="text-center">Batches</th>
                    <th class="text-center">Quantity</th>
                    <th class="text-end">Est. Cost</th>
                </tr>
            </thead>
            <tbody>
                {% for item in product_breakdown %}
                <tr>
                    <td><strong>{{ item.product_name }}</strong></td>
                    <td class="text-center">{{ item.batch_count }}</td>
                    <td class="text-center"><strong>{{ item.quantity|intcomma }}</strong></td>
                    <td class="text-end text-warning">KES {{ item.cost|floatformat:0|intcomma }}</td>
                </tr>
                {% endfor %}
            </tbody>
            <tfoot>
                <tr>
                    <td><strong>TOTAL</strong></td>
                    <td class="text-center"><strong>{{ batch_count }}</strong></td>
                    <td class="text-center"><strong>{{ total_quantity|intcomma }}</strong></td>
                    <td class="text-end text-warning"><strong>KES {{ total_cost|floatformat:0|intcomma }}</strong></td>
                </tr>
            </tfoot>
        </table>
        {% else %}
        <div class="empty-state">
            <i class="bi bi-inbox empty-state__icon"></i>
            <p class="empty-state__text">No production data for this date.</p>
        </div>
        {% endif %}
    </div>
</div>

<!-- Batch Details -->
<div class="report-section mb-4">
    <div class="report-section__header">
        <h3 class="report-section__title"><i class="bi bi-list-ul"></i> Batch Details</h3>
    </div>
    <div class="report-section__body p-0">
        {% if batches %}
        <table class="data-table">
            <thead>
                <tr>
                    <th>Batch #</th>
                    <th>Product</th>
                    <th class="text-center">Quantity</th>
                    <th>Status</th>
                    <th>Notes</th>
                </tr>
            </thead>
            <tbody>
                {% for batch in batches %}
                <tr>
                    <td><code>{{ batch.batch_number }}</code></td>
                    <td>{{ batch.product_name }}</td>
                    <td class="text-center">{{ batch.quantity|intcomma }}</td>
                    <td><span class="status-badge status-badge--{{ batch.status_color }}">{{ batch.status }}</span></td>
                    <td class="text-muted">{{ batch.notes|default:"-"|truncatewords:10 }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state">
            <i class="bi bi-inbox empty-state__icon"></i>
            <p class="empty-state__text">No batches for this date.</p>
        </div>
        {% endif %}
    </div>
</div>

<!-- Export Actions -->
<div class="d-flex justify-content-end gap-2">
    <a href="{% url 'reports:export_csv' %}?type=production_daily&date={{ report_date|date:'Y-m-d' }}" class="btn btn-outline-success">
        <i class="bi bi-download me-1"></i> Export CSV
    </a>
    <a href="{% url 'reports:production_index' %}" class="btn btn-outline-secondary">
        <i class="bi bi-arrow-left me-1"></i> Back to Production Reports
    </a>
</div>
{% endblock %}
'''
    with open(path, 'w') as f:
        f.write(content)
    print(f"✅ Updated {path}")

if __name__ == "__main__":
    update_production_daily()
