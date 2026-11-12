
def _register(client, username="recipe_user"):
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "RecipePass123",
        },
    )
    assert response.status_code == 201, response.text


def test_recipes_require_login(isolated_client):
    assert isolated_client.get("/api/recipes").status_code == 401
    assert isolated_client.post(
        "/api/recipes",
        json={"name": "My recipe", "steps": [{"step_type": "standardize_nulls", "config": {}}]},
    ).status_code == 401


def test_list_create_apply_update_and_delete_recipe(isolated_client):
    client = isolated_client
    _register(client)

    listed = client.get("/api/recipes")
    assert listed.status_code == 200
    recipes = listed.json()["recipes"]
    assert any(recipe["is_public"] for recipe in recipes)
    # Legacy seed rows are normalized to the current step_type contract.
    assert all("step_type" in step for recipe in recipes for step in recipe["steps"])

    created = client.post(
        "/api/recipes",
        json={
            "name": "My Median Recipe",
            "description": "Fill missing numeric values",
            "steps": [
                {"step_type": "missing_values", "config": {"columns": [], "strategy": "median"}},
                {"step_type": "scaling", "config": {"columns": [], "method": "min_max"}},
            ],
        },
    )
    assert created.status_code == 201, created.text
    recipe = created.json()["recipe"]
    recipe_id = recipe["id"]
    assert recipe["is_owner"] is True

    applied = client.post(f"/api/recipes/{recipe_id}/apply")
    assert applied.status_code == 200
    assert applied.json()["pipeline"][0]["step_type"] == "missing_values"

    updated = client.put(
        f"/api/recipes/{recipe_id}",
        json={"description": "Updated description"},
    )
    assert updated.status_code == 200
    assert updated.json()["recipe"]["description"] == "Updated description"

    deleted = client.delete(f"/api/recipes/{recipe_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/recipes/{recipe_id}").status_code == 404


def test_recipe_is_private_to_its_owner(isolated_client):
    client = isolated_client
    _register(client, "first_user")
    created = client.post(
        "/api/recipes",
        json={"name": "Private", "steps": [{"step_type": "standardize_nulls", "config": {}}]},
    )
    recipe_id = created.json()["recipe"]["id"]

    client.post("/api/auth/logout")
    _register(client, "second_user")
    assert client.get(f"/api/recipes/{recipe_id}").status_code == 404
    assert client.delete(f"/api/recipes/{recipe_id}").status_code == 404

    # Second user must not see first user's recipe in the list
    second_recipes = client.get("/api/recipes").json()["recipes"]
    assert not any(r["id"] == recipe_id for r in second_recipes)

    # First user logs back in and sees their recipe isolated
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "first_user", "password": "RecipePass123"})
    first_recipes = client.get("/api/recipes").json()["recipes"]
    matching = [r for r in first_recipes if r["id"] == recipe_id]
    assert len(matching) == 1
    assert matching[0]["is_owner"] is True


def test_builtin_recipe_can_be_applied_and_run(isolated_client):
    import pandas as pd

    from backend.services.pipeline_runner import run_selected_pipeline

    client = isolated_client
    _register(client, "builtin_user")
    recipes = client.get("/api/recipes").json()["recipes"]
    builtin = next(recipe for recipe in recipes if recipe["is_public"])
    applied = client.post(f"/api/recipes/{builtin['id']}/apply")
    assert applied.status_code == 200, applied.text

    frame = pd.DataFrame(
        {
            "age": [20.0, None, 30.0, 40.0, 50.0],
            "city": ["Hanoi", "HCM", "Hanoi", "Hue", "HCM"],
        }
    )
    cleaned, _ = run_selected_pipeline(frame, applied.json()["pipeline"])
    assert isinstance(cleaned, pd.DataFrame)
    assert len(cleaned) > 0
