from flask import current_app as app, render_template, request, redirect, abort, jsonify, url_for, session, Blueprint, \
    Response, send_file
from CTFd.models import db, Users, Teams, Solves, Awards, Files, Pages, Tracking
from CTFd.utils.decorators import authed_only
from CTFd.utils.decorators.modes import require_team_mode
from CTFd.utils.modes import USERS_MODE
from CTFd.utils import config, get_config, set_config
from CTFd.utils.user import get_current_user, authed, get_ip
from CTFd.utils.dates import unix_time_to_utc
from CTFd.utils.crypto import verify_password
from CTFd.utils.decorators.visibility import check_account_visibility, check_score_visibility

teams = Blueprint('teams', __name__)


@teams.route('/teams')
@check_account_visibility
@require_team_mode
def listing():
    if get_config('user_mode') == USERS_MODE:
        return redirect(url_for('users.listing'))
    page = request.args.get('page', 1)
    page = abs(int(page))
    results_per_page = 50
    page_start = results_per_page * (page - 1)
    page_end = results_per_page * (page - 1) + results_per_page

    # TODO: Should teams confirm emails?
    # if get_config('verify_emails'):
    #     count = Teams.query.filter_by(verified=True, banned=False).count()
    #     teams = Teams.query.filter_by(verified=True, banned=False).slice(page_start, page_end).all()
    # else:
    count = Teams.query.filter_by(banned=False).count()
    teams = Teams.query.filter_by(banned=False).slice(page_start, page_end).all()

    pages = int(count / results_per_page) + (count % results_per_page > 0)
    return render_template('teams/teams.html', teams=teams, pages=pages, curr_page=page)


@teams.route('/teams/join', methods=['GET', 'POST'])
@authed_only
@require_team_mode
def join():
    if request.method == 'GET':
        return render_template('teams/join_team.html')
    if request.method == 'POST':
        teamname = request.form.get('name')
        passphrase = request.form.get('password', '').strip()

        team = Teams.query.filter_by(name=teamname).first()
        user = get_current_user()
        if team and verify_password(passphrase, team.password):
            user.team_id = team.id
            db.session.commit()
            return redirect(url_for('challenges.listing'))
        else:
            errors = ['That information is incorrect']
            return render_template('teams/join_team.html', errors=errors)


@teams.route('/teams/new', methods=['GET', 'POST'])
@authed_only
@require_team_mode
def new():
    if request.method == 'GET':
        return render_template("teams/new_team.html")
    elif request.method == 'POST':
        teamname = request.form.get('name')
        passphrase = request.form.get('password', '').strip()
        errors = []

        user = get_current_user()

        existing_team = Teams.query.filter_by(name=teamname).first()
        if existing_team:
            errors.append('That team name is already taken')

        if errors:
            return render_template("teams/new_team.html", errors=errors)

        team = Teams(
            name=teamname,
            password=passphrase
        )

        db.session.add(team)
        db.session.commit()

        user.team_id = team.id
        db.session.commit()
        return redirect(url_for('challenges.listing'))


@teams.route('/team', methods=['GET'])
@authed_only
@require_team_mode
def private():
    user = get_current_user()
    if not user.team_id:
        return render_template(
            'teams/team_enrollment.html',
        )

    team_id = user.team_id

    team = Teams.query.filter_by(id=team_id).first_or_404()
    solves = team.get_solves()
    awards = team.get_awards()

    place = team.place
    score = team.score

    return render_template(
        'teams/team.html',
        solves=solves,
        awards=awards,
        team=team,
        score=score,
        place=place,
        score_frozen=config.is_scoreboard_frozen()
    )


@teams.route('/teams/<int:team_id>', methods=['GET', 'POST'])
@check_account_visibility
@check_score_visibility
@require_team_mode
def public(team_id):
    errors = []
    team = Teams.query.filter_by(id=team_id).first_or_404()
    solves = team.get_solves()
    awards = team.get_awards()

    place = team.place
    score = team.score

    if errors:
        return render_template('teams/team.html', team=team, errors=errors)

    if request.method == 'GET':
        return render_template(
            'teams/team.html',
            solves=solves,
            awards=awards,
            team=team,
            score=score,
            place=place,
            score_frozen=config.is_scoreboard_frozen()
        )
